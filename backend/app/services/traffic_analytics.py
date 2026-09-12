import os
import time
import uuid
import math
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set
from app.config import get_settings

logger = logging.getLogger(__name__)

# Configurable Default Thresholds
DEFAULT_STATIONARY_DISTANCE_PX = 30.0
DEFAULT_STATIONARY_DURATION_SEC = 60.0
DEFAULT_HIGH_TRAFFIC_THRESHOLD = 16
DEFAULT_VERY_HIGH_TRAFFIC_THRESHOLD = 31

EVENT_COOLDOWN_HIGH_TRAFFIC = 60.0  # seconds
EVENT_COOLDOWN_VERY_HIGH = 60.0
EVENT_COOLDOWN_STATIONARY = 120.0

class CameraTrafficAnalytics:
    """
    Maintains real-time traffic statistics, vehicle class counting, active track state,
    stationary vehicle detection, and event management per camera feed.
    Supports Phase 11 6-class tracking: car, motorcycle, bus, truck, auto_rickshaw, ambiguous.
    """
    def __init__(self, camera_id: str):
        self.camera_id = camera_id
        self.seen_track_ids: Set[int] = set()
        self.vehicle_type_counts: Dict[str, int] = {
            "car": 0, "motorcycle": 0, "bus": 0, "truck": 0, "auto_rickshaw": 0, "ambiguous": 0
        }
        
        # Track lifecycle history: track_id -> metadata
        self.tracks_history: Dict[int, Dict[str, Any]] = {}
        self.active_tracks: Dict[int, Dict[str, Any]] = {}
        
        # Event store & cooldown trackers
        self.events: List[Dict[str, Any]] = []
        self.event_cooldowns: Dict[str, float] = {}
        
        self.start_time: float = time.time()
        self.last_update_time: float = time.time()
        self.active_count_samples: List[int] = []

    def reset(self):
        self.seen_track_ids.clear()
        self.tracks_history.clear()
        self.active_tracks.clear()
        self.events.clear()
        self.event_cooldowns.clear()
        self.active_count_samples.clear()
        for k in self.vehicle_type_counts:
            self.vehicle_type_counts[k] = 0
        self.start_time = time.time()
        self.last_update_time = time.time()

    def classify_density(self, active_count: int) -> str:
        if active_count <= 5:
            return "LOW"
        elif active_count <= 15:
            return "MODERATE"
        elif active_count <= 30:
            return "HIGH"
        else:
            return "VERY_HIGH"

    def _can_fire_event(self, event_key: str, cooldown_seconds: float, current_time: float) -> bool:
        last_fired = self.event_cooldowns.get(event_key, 0.0)
        if (current_time - last_fired) >= cooldown_seconds:
            self.event_cooldowns[event_key] = current_time
            return True
        return False

    def update(self, detections: List[Dict[str, Any]], current_time: float = None) -> Dict[str, Any]:
        if current_time is None:
            current_time = time.time()
        if not self.active_count_samples:
            self.start_time = current_time
        self.last_update_time = current_time
        current_active_ids: Set[int] = set()

        for d in detections:
            tid = d.get("track_id")
            if tid is None:
                continue

            current_active_ids.add(tid)
            vtype = d.get("vehicle_type", "car").lower()
            if vtype not in self.vehicle_type_counts:
                vtype = "car"

            bbox = d.get("bbox", [0, 0, 0, 0])
            cx = (bbox[0] + bbox[2]) / 2.0
            cy = (bbox[1] + bbox[3]) / 2.0

            # 1. Unique Vehicle Counting & Track History Update
            if tid not in self.seen_track_ids:
                self.seen_track_ids.add(tid)
                self.vehicle_type_counts[vtype] = self.vehicle_type_counts.get(vtype, 0) + 1

                self.tracks_history[tid] = {
                    "track_id": tid,
                    "vehicle_type": vtype,
                    "first_seen": current_time,
                    "last_seen": current_time,
                    "detection_count": 1,
                    "initial_center": (cx, cy),
                    "last_center": (cx, cy),
                    "trajectory": [(cx, cy)],
                    "stationary_start_time": None,
                    "is_stationary": False,
                    "stationary_duration": 0.0,
                    "latest_bbox": bbox
                }
            else:
                tinfo = self.tracks_history[tid]
                old_vtype = tinfo["vehicle_type"]
                
                # Update vehicle_type if temporal voting changed it
                if old_vtype != vtype:
                    self.vehicle_type_counts[old_vtype] = max(0, self.vehicle_type_counts.get(old_vtype, 1) - 1)
                    self.vehicle_type_counts[vtype] = self.vehicle_type_counts.get(vtype, 0) + 1
                    tinfo["vehicle_type"] = vtype

                tinfo["last_seen"] = current_time
                tinfo["detection_count"] += 1
                tinfo["latest_bbox"] = bbox
                tinfo["trajectory"].append((cx, cy))
                if len(tinfo["trajectory"]) > 40:
                    tinfo["trajectory"].pop(0)
                
                # Check displacement from initial center for stationary detection
                icx, icy = tinfo["initial_center"]
                dist = math.hypot(cx - icx, cy - icy)

                if dist <= DEFAULT_STATIONARY_DISTANCE_PX:
                    if tinfo["stationary_start_time"] is None:
                        tinfo["stationary_start_time"] = current_time
                    
                    tinfo["stationary_duration"] = current_time - tinfo["stationary_start_time"]

                    if tinfo["stationary_duration"] >= DEFAULT_STATIONARY_DURATION_SEC:
                        tinfo["is_stationary"] = True
                else:
                    # Vehicle moved beyond threshold -> reset initial center
                    tinfo["initial_center"] = (cx, cy)
                    tinfo["stationary_start_time"] = None
                    tinfo["is_stationary"] = False
                    tinfo["stationary_duration"] = 0.0

                tinfo["last_center"] = (cx, cy)

        # Update active tracks dictionary
        self.active_tracks = {
            tid: self.tracks_history[tid] for tid in current_active_ids if tid in self.tracks_history
        }

        active_count = len(current_active_ids)
        self.active_count_samples.append(active_count)
        if len(self.active_count_samples) > 200:
            self.active_count_samples.pop(0)

        density = self.classify_density(active_count)

        # Phase 9: Incident Engine Evaluation
        from app.services.incident_detector import incident_engine
        cam_events = incident_engine.evaluate_frame_events(self.camera_id, self.active_tracks, density, current_time)
        self.events = cam_events

        return self.get_analytics()

    def get_analytics(self) -> Dict[str, Any]:
        total_unique = len(self.seen_track_ids)
        active_vehicles = len(self.active_tracks)

        active_cars = sum(1 for t in self.active_tracks.values() if t["vehicle_type"] == "car")
        active_motos = sum(1 for t in self.active_tracks.values() if t["vehicle_type"] == "motorcycle")
        active_buses = sum(1 for t in self.active_tracks.values() if t["vehicle_type"] == "bus")
        active_trucks = sum(1 for t in self.active_tracks.values() if t["vehicle_type"] == "truck")
        active_rickshaws = sum(1 for t in self.active_tracks.values() if t["vehicle_type"] == "auto_rickshaw")
        active_ambiguous = sum(1 for t in self.active_tracks.values() if t["vehicle_type"] == "ambiguous")

        # Class Distribution %
        if total_unique > 0:
            dist = {
                "car": round((self.vehicle_type_counts.get("car", 0) / float(total_unique)) * 100.0, 1),
                "motorcycle": round((self.vehicle_type_counts.get("motorcycle", 0) / float(total_unique)) * 100.0, 1),
                "bus": round((self.vehicle_type_counts.get("bus", 0) / float(total_unique)) * 100.0, 1),
                "truck": round((self.vehicle_type_counts.get("truck", 0) / float(total_unique)) * 100.0, 1),
                "auto_rickshaw": round((self.vehicle_type_counts.get("auto_rickshaw", 0) / float(total_unique)) * 100.0, 1),
                "ambiguous": round((self.vehicle_type_counts.get("ambiguous", 0) / float(total_unique)) * 100.0, 1)
            }
        else:
            dist = {"car": 0.0, "motorcycle": 0.0, "bus": 0.0, "truck": 0.0, "auto_rickshaw": 0.0, "ambiguous": 0.0}

        # Flow Metrics
        elapsed_min = max(0.1, (self.last_update_time - self.start_time) / 60.0)
        vpm = round(total_unique / elapsed_min, 1)
        avg_active = round(float(sum(self.active_count_samples)) / max(1, len(self.active_count_samples)), 1) if self.active_count_samples else 0.0

        stationary_list = [
            {
                "track_id": t["track_id"],
                "vehicle_type": t["vehicle_type"],
                "status": "STATIONARY",
                "stationary_duration_seconds": round(t["stationary_duration"], 1)
            }
            for t in self.tracks_history.values() if t.get("is_stationary")
        ]

        return {
            "camera_id": self.camera_id,
            "total_unique_vehicles": total_unique,
            "unique_vehicle_breakdown": {
                "cars": self.vehicle_type_counts.get("car", 0),
                "motorcycles": self.vehicle_type_counts.get("motorcycle", 0),
                "buses": self.vehicle_type_counts.get("bus", 0),
                "trucks": self.vehicle_type_counts.get("truck", 0),
                "auto_rickshaws": self.vehicle_type_counts.get("auto_rickshaw", 0),
                "ambiguous_vehicles": self.vehicle_type_counts.get("ambiguous", 0)
            },
            "active_vehicles": active_vehicles,
            "active_vehicle_breakdown": {
                "active_cars": active_cars,
                "active_motorcycles": active_motos,
                "active_buses": active_buses,
                "active_trucks": active_trucks,
                "active_auto_rickshaws": active_rickshaws,
                "active_ambiguous_vehicles": active_ambiguous
            },
            "traffic_density": self.classify_density(active_vehicles),
            "distribution_percentage": dist,
            "flow_metrics": {
                "average_active_vehicles": avg_active,
                "vehicles_per_minute": vpm,
                "vehicles_entered_count": total_unique,
                "vehicles_left_count": max(0, total_unique - active_vehicles)
            },
            "stationary_vehicles": stationary_list,
            "recent_events_count": len(self.events),
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

class TrafficAnalyticsEngine:
    """
    System-Wide Multi-Camera Traffic Analytics Engine orchestrating isolated
    per-camera statistics and global multi-camera summaries.
    """
    def __init__(self):
        self.cameras: Dict[str, CameraTrafficAnalytics] = {}

    def reset(self):
        self.seen_track_ids.clear()
        self.tracks_history.clear()
        self.active_tracks.clear()
        self.events.clear()
        self.event_cooldowns.clear()
        self.active_count_samples.clear()
        for k in self.vehicle_type_counts:
            self.vehicle_type_counts[k] = 0
        self.start_time = time.time()
        self.last_update_time = time.time()

    def get_camera_analytics(self, camera_id: str) -> CameraTrafficAnalytics:
        if camera_id not in self.cameras:
            self.cameras[camera_id] = CameraTrafficAnalytics(camera_id)
        return self.cameras[camera_id]

    def reset_camera_tracking(self, camera_id: str):
        if camera_id in self.cameras:
            self.cameras[camera_id] = CameraTrafficAnalytics(camera_id)

    def update_camera_detections(self, camera_id: str, detections: List[Dict[str, Any]], current_time=None) -> Dict[str, Any]:
        cam_analytics = self.get_camera_analytics(camera_id)
        return cam_analytics.update(detections,current_time=current_time)

    def get_all_analytics(self) -> List[Dict[str, Any]]:
        return [cam.get_analytics() for cam in self.cameras.values()]

    def get_system_summary(self) -> Dict[str, Any]:
        all_analytics = self.get_all_analytics()
        total_cams = len(all_analytics)
        online_cams = sum(1 for a in all_analytics if a.get("active_vehicles", 0) >= 0)
        total_active_veh = sum(a.get("active_vehicles", 0) for a in all_analytics)

        density_counts = {"LOW": 0, "MODERATE": 0, "HIGH": 0, "VERY_HIGH": 0}
        for a in all_analytics:
            d = a.get("traffic_density", "LOW")
            density_counts[d] = density_counts.get(d, 0) + 1

        busiest_cam = None
        max_active = -1
        for a in all_analytics:
            if a["active_vehicles"] > max_active:
                max_active = a["active_vehicles"]
                busiest_cam = a["camera_id"]

        return {
            "total_cameras": total_cams,
            "online_cameras": online_cams,
            "total_active_vehicles": total_active_veh,
            "traffic_density_summary": density_counts,
            "busiest_camera": busiest_cam,
            "highest_active_vehicle_count": max_active if max_active >= 0 else 0,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    def get_events(
        self,
        camera_id: Optional[str] = None,
        event_type: Optional[str] = None,
        severity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        all_events = []
        for cam in self.cameras.values():
            if camera_id and cam.camera_id != camera_id:
                continue
            for evt in cam.events:
                if event_type and evt.get("event_type") != event_type:
                    continue
                if severity and evt.get("severity") != severity:
                    continue
                all_events.append(evt)

        all_events.sort(key=lambda e: e.get("timestamp", ""), reverse=True)
        return all_events

# Global singleton instance
traffic_analytics_engine = TrafficAnalyticsEngine()
