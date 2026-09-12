import os
import time
import uuid
import math
import logging
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Set

logger = logging.getLogger(__name__)

# Organizer names do not establish permitted road direction. Configure only
# after verifying the actual scene and traffic rules for that camera.
DEFAULT_CAMERA_CONFIGS: Dict[str, Dict[str, Any]] = {}

EVENT_COOLDOWNS: Dict[str, float] = {
    "HIGH_TRAFFIC": 60.0,
    "VERY_HIGH_TRAFFIC": 60.0,
    "STATIONARY_VEHICLE": 120.0,
    "WRONG_DIRECTION": 120.0,
    "POSSIBLE_CONGESTION": 120.0,
    "POSSIBLE_INCIDENT": 180.0
}

class IncidentDetectionEngine:
    """
    Phase 9 Service: Intelligent Traffic Event & Incident Detection Engine.
    Evaluates tracking trajectories, movement vectors, stationary behavior,
    wrong-way direction monitoring, congestion patterns, and conservative incident rules.
    """
    def __init__(self):
        self.camera_configs = DEFAULT_CAMERA_CONFIGS
        # Managed events store: list of event dicts
        self.events_db: List[Dict[str, Any]] = []
        self.event_cooldown_tracker: Dict[str, float] = {}
        self.session_events_count: int = 0
        self.session_start_time: float = time.time()

    def reset_session(self):
        """Reset session event counters for a clean benchmark test run."""
        self.session_events_count = 0
        self.session_start_time = time.time()

    def reset_camera(self, camera_id):
        for event in self.events_db:
            if event['camera_id'] == camera_id and event['status'] == 'ACTIVE':
                event['status'] = 'EXPIRED'
        self.event_cooldown_tracker = {k:v for k,v in self.event_cooldown_tracker.items() if not (k.endswith('_'+camera_id) or ('_'+camera_id+'_') in k)}

    def get_camera_config(self, camera_id: str) -> Dict[str, Any]:
        return self.camera_configs.get(camera_id, {
            "expected_direction": "UNKNOWN",
            "stationary_threshold_seconds": 60.0,
            "enable_wrong_direction": False
        })

    def _can_fire_event(self, event_key: str, cooldown_seconds: float, current_time: float) -> bool:
        last_fired = self.event_cooldown_tracker.get(event_key, 0.0)
        if (current_time - last_fired) >= cooldown_seconds:
            self.event_cooldown_tracker[event_key] = current_time
            return True
        return False

    def calculate_direction_vector(self, trajectory: List[tuple]) -> Optional[str]:
        """
        Calculates movement vector from trajectory history (first point vs recent point).
        Requires at least 5 frames and displacement >= 35 pixels to avoid jitter.
        """
        if len(trajectory) < 5:
            return None

        p_start = trajectory[0]
        p_end = trajectory[-1]

        dx = p_end[0] - p_start[0]
        dy = p_end[1] - p_start[1]
        dist = math.hypot(dx, dy)

        if dist < 35.0:
            return None  # Insufficient movement

        if abs(dx) > abs(dy):
            return "LEFT_TO_RIGHT" if dx > 0 else "RIGHT_TO_LEFT"
        else:
            return "TOP_TO_BOTTOM" if dy > 0 else "BOTTOM_TO_TOP"

    def is_wrong_direction(self, actual_direction: str, expected_direction: str) -> bool:
        opposites = {
            "LEFT_TO_RIGHT": "RIGHT_TO_LEFT",
            "RIGHT_TO_LEFT": "LEFT_TO_RIGHT",
            "TOP_TO_BOTTOM": "BOTTOM_TO_TOP",
            "BOTTOM_TO_TOP": "TOP_TO_BOTTOM"
        }
        return opposites.get(expected_direction) == actual_direction

    def evaluate_frame_events(
        self,
        camera_id: str,
        active_tracks: Dict[int, Dict[str, Any]],
        traffic_density: str,
        current_time: float = None
    ) -> List[Dict[str, Any]]:
        if current_time is None:
            current_time = time.time()

        cam_cfg = self.get_camera_config(camera_id)
        expected_dir = cam_cfg.get("expected_direction", "UNKNOWN")
        stat_thresh_sec = cam_cfg.get("stationary_threshold_seconds", 60.0)
        enable_wd = cam_cfg.get("enable_wrong_direction", True)

        active_count = len(active_tracks)

        # 1. Update Existing Event Lifecycles (ACTIVE -> RESOLVED / EXPIRED)
        for evt in self.events_db:
            if evt["camera_id"] == camera_id and evt["status"] == "ACTIVE":
                etype = evt["event_type"]

                # Resolve HIGH_TRAFFIC / VERY_HIGH_TRAFFIC if density drops
                if etype in ["HIGH_TRAFFIC", "VERY_HIGH_TRAFFIC"]:
                    if traffic_density in ["LOW", "MODERATE"]:
                        evt["status"] = "RESOLVED"
                        evt["resolved_timestamp"] = datetime.now(timezone.utc).isoformat()

                # Resolve STATIONARY_VEHICLE if vehicle moves or leaves
                elif etype == "STATIONARY_VEHICLE":
                    tid = evt.get("track_id")
                    if tid not in active_tracks or not active_tracks[tid].get("is_stationary", False):
                        evt["status"] = "RESOLVED"
                        evt["resolved_timestamp"] = datetime.now(timezone.utc).isoformat()

                # Resolve POSSIBLE_CONGESTION if count drops or movement increases
                elif etype == "POSSIBLE_CONGESTION":
                    if active_count < 10:
                        evt["status"] = "RESOLVED"
                        evt["resolved_timestamp"] = datetime.now(timezone.utc).isoformat()

        # 2. Detector 1: HIGH_TRAFFIC & VERY_HIGH_TRAFFIC
        if traffic_density == "HIGH":
            ekey = f"HIGH_TRAFFIC_{camera_id}"
            if self._can_fire_event(ekey, EVENT_COOLDOWNS["HIGH_TRAFFIC"], current_time):
                self._add_event({
                    "event_id": str(uuid.uuid4()),
                    "event_type": "HIGH_TRAFFIC",
                    "camera_id": camera_id,
                    "track_id": None,
                    "vehicle_type": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.90,
                    "severity": "MEDIUM",
                    "status": "ACTIVE",
                    "metadata": {"active_vehicles": active_count, "traffic_density": traffic_density}
                })
        elif traffic_density == "VERY_HIGH":
            ekey = f"VERY_HIGH_{camera_id}"
            if self._can_fire_event(ekey, EVENT_COOLDOWNS["VERY_HIGH_TRAFFIC"], current_time):
                self.events_db.append({
                    "event_id": str(uuid.uuid4()),
                    "event_type": "VERY_HIGH_TRAFFIC",
                    "camera_id": camera_id,
                    "track_id": None,
                    "vehicle_type": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.95,
                    "severity": "HIGH",
                    "status": "ACTIVE",
                    "metadata": {"active_vehicles": active_count, "traffic_density": traffic_density}
                })

        # 3. Detector 2 & 3: Per-Track Stationary, Wrong Direction, & Sudden Stop Incident
        avg_movements = []
        sudden_stops_count = 0

        for tid, tinfo in active_tracks.items():
            vtype = tinfo.get("vehicle_type", "car")
            traj = tinfo.get("trajectory", [])
            dur = tinfo.get("stationary_duration", 0.0)
            is_stat = tinfo.get("is_stationary", False)

            # Measure movement delta over trajectory
            if len(traj) >= 2:
                recent_dist = math.hypot(traj[-1][0] - traj[-2][0], traj[-1][1] - traj[-2][0])
                avg_movements.append(recent_dist)
            else:
                avg_movements.append(0.0)

            # STATIONARY_VEHICLE Event
            if (dur >= stat_thresh_sec or is_stat):
                ekey = f"STATIONARY_{camera_id}_{tid}"
                if self._can_fire_event(ekey, EVENT_COOLDOWNS["STATIONARY_VEHICLE"], current_time):
                    self.events_db.append({
                        "event_id": str(uuid.uuid4()),
                        "event_type": "STATIONARY_VEHICLE",
                        "camera_id": camera_id,
                        "track_id": tid,
                        "vehicle_type": vtype,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "confidence": 0.88,
                        "severity": "MEDIUM",
                        "status": "ACTIVE",
                        "metadata": {
                            "stationary_duration_seconds": round(dur, 1),
                            "bbox": tinfo.get("latest_bbox", [])
                        }
                    })

            # WRONG_DIRECTION Event
            if enable_wd and expected_dir != "UNKNOWN" and len(traj) >= 8:
                actual_dir = self.calculate_direction_vector(traj)
                if actual_dir and self.is_wrong_direction(actual_dir, expected_dir):
                    ekey = f"WRONG_DIR_{camera_id}_{tid}"
                    if self._can_fire_event(ekey, EVENT_COOLDOWNS["WRONG_DIRECTION"], current_time):
                        self.events_db.append({
                            "event_id": str(uuid.uuid4()),
                            "event_type": "WRONG_DIRECTION",
                            "camera_id": camera_id,
                            "track_id": tid,
                            "vehicle_type": vtype,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "confidence": 0.82,
                            "severity": "HIGH",
                            "status": "ACTIVE",
                            "metadata": {
                                "direction": actual_dir,
                                "expected_direction": expected_dir,
                                "bbox": tinfo.get("latest_bbox", [])
                            }
                        })

            # Detect Sudden Stop Pattern (Sudden drop from high movement to 0)
            if len(traj) >= 12 and is_stat and dur >= 15.0:
                p_early = traj[0]
                p_mid = traj[5]
                early_dist = math.hypot(p_mid[0] - p_early[0], p_mid[1] - p_early[1])
                if early_dist >= 50.0:
                    sudden_stops_count += 1
                    ekey = f"POSSIBLE_INCIDENT_{camera_id}_{tid}"
                    if self._can_fire_event(ekey, EVENT_COOLDOWNS["POSSIBLE_INCIDENT"], current_time):
                        self.events_db.append({
                            "event_id": str(uuid.uuid4()),
                            "event_type": "POSSIBLE_INCIDENT",
                            "camera_id": camera_id,
                            "track_id": tid,
                            "vehicle_type": vtype,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                            "confidence": 0.68,
                            "severity": "HIGH",
                            "status": "ACTIVE",
                            "metadata": {
                                "reason": "sudden_stop_followed_by_stationary_behavior",
                                "stationary_duration": round(dur, 1),
                                "bbox": tinfo.get("latest_bbox", [])
                            }
                        })

        # 4. Detector 4: POSSIBLE_CONGESTION
        mean_movement = float(np.mean(avg_movements)) if avg_movements else 0.0
        if active_count >= 12 and mean_movement < 8.0:
            ekey = f"CONGESTION_{camera_id}"
            if self._can_fire_event(ekey, EVENT_COOLDOWNS["POSSIBLE_CONGESTION"], current_time):
                self.events_db.append({
                    "event_id": str(uuid.uuid4()),
                    "event_type": "POSSIBLE_CONGESTION",
                    "camera_id": camera_id,
                    "track_id": None,
                    "vehicle_type": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "confidence": 0.75,
                    "severity": "MEDIUM",
                    "status": "ACTIVE",
                    "metadata": {
                        "active_vehicles": active_count,
                        "average_vehicle_movement": round(mean_movement, 2),
                        "traffic_density": traffic_density
                    }
                })

        return [e for e in self.events_db if e["camera_id"] == camera_id]

    def _add_event(self, evt: Dict[str, Any]):
        self.events_db.append(evt)
        self.session_events_count += 1

    def get_events_summary(self) -> Dict[str, Any]:
        total_events = len(self.events_db)
        active_events = sum(1 for e in self.events_db if e.get("status") == "ACTIVE")
        
        by_type: Dict[str, int] = {}
        by_camera: Dict[str, int] = {}

        for e in self.events_db:
            et = e.get("event_type", "OTHER")
            cid = e.get("camera_id", "UNKNOWN")
            by_type[et] = by_type.get(et, 0) + 1
            by_camera[cid] = by_camera.get(cid, 0) + 1

        recent = sorted(self.events_db, key=lambda e: e.get("timestamp", ""), reverse=True)[:10]

        return {
            "session_events": self.session_events_count,
            "historical_events": total_events,
            "total_events": total_events,
            "active_events": active_events,
            "by_type": by_type,
            "by_camera": by_camera,
            "recent_events": recent,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

# Global singleton instance
incident_engine = IncidentDetectionEngine()
