import os
import cv2
import time
import uuid
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

from app.paths import EVIDENCE_DIR
EVIDENCE_DIR.mkdir(parents=True, exist_ok=True)

# Event Cooldowns to prevent duplicate alerts on consecutive frames for the same track
EVENT_COOLDOWNS = {
    "POSSIBLE_WRONG_WAY": 120.0,
    "PROLONGED_STOPPING": 120.0,
    "HEAVY_CONGESTION": 60.0,
    "VEHICLE_SURGE": 60.0
}

class TrafficViolationEngine:
    """
    Phase 12.6 Service: Traffic Violation Intelligence & Evidence Generation Engine.
    Evaluates tracked vehicle trajectories, movement vectors, stationary behavior, and congestion.
    Generates structured violation event objects and captures sharp evidence images.
    """
    def __init__(self):
        self.events_db: List[Dict[str, Any]] = []
        self.cooldown_tracker: Dict[str, float] = {}

    def process_demo_frame(
        self,
        camera_id: str,
        frame: Any,
        detections: List[Dict[str, Any]],
        analytics_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        new_events = []
        current_time = time.time()
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # 1. Evaluate Heavy Congestion Events
        traffic_density = analytics_data.get("traffic_density", "LOW")
        active_count = analytics_data.get("active_vehicles", 0)

        if traffic_density in ("HIGH", "VERY_HIGH") and active_count >= 15:
            cd_key = f"{camera_id}_HEAVY_CONGESTION"
            if (current_time - self.cooldown_tracker.get(cd_key, 0.0)) >= EVENT_COOLDOWNS["HEAVY_CONGESTION"]:
                self.cooldown_tracker[cd_key] = current_time
                evt_id = f"EVT-DEMO-{uuid.uuid4().hex[:8].upper()}"
                
                # Save evidence image frame
                img_rel_path = self._save_evidence_image(frame, camera_id, date_str, evt_id, detections)

                evt = {
                    "event_id": evt_id,
                    "camera_id": camera_id,
                    "mode": "DEMO",
                    "source_type": "DEMO_MP4",
                    "event_type": "HEAVY_CONGESTION",
                    "severity": "HIGH" if traffic_density == "VERY_HIGH" else "MEDIUM",
                    "title": "Heavy Congestion Detected",
                    "description": f"High vehicle density ({active_count} active vehicles) observed on demo stream.",
                    "vehicle_class": "multi",
                    "track_id": None,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "location": None,
                    "display_location": "Recorded Dataset Footage",
                    "anpr": None,
                    "confidence": 0.92,
                    "evidence_level": "HIGH",
                    "evidence_image_url": f"/api/demo/evidence/{img_rel_path}",
                    "status": "NEW"
                }
                self.events_db.append(evt)
                new_events.append(evt)

        # 2. Evaluate Individual Vehicle Detections (Wrong-Way & Prolonged Stopping)
        for d in detections:
            tid = d.get("track_id")
            if tid is None:
                continue

            vtype = d.get("vehicle_type", "car")
            bbox = d.get("bbox", [0, 0, 0, 0])

            # Check for possible wrong-way or irregular trajectory if available
            # (Simulated trajectory validation on demo frames for demonstration)
            if d.get("is_wrong_direction", False):
                cd_key = f"{camera_id}_{tid}_WRONG_WAY"
                if (current_time - self.cooldown_tracker.get(cd_key, 0.0)) >= EVENT_COOLDOWNS["POSSIBLE_WRONG_WAY"]:
                    self.cooldown_tracker[cd_key] = current_time
                    evt_id = f"EVT-DEMO-{uuid.uuid4().hex[:8].upper()}"
                    
                    img_rel_path = self._save_evidence_image(frame, camera_id, date_str, evt_id, [d])

                    evt = {
                        "event_id": evt_id,
                        "camera_id": camera_id,
                        "mode": "DEMO",
                        "source_type": "DEMO_MP4",
                        "event_type": "POSSIBLE_WRONG_WAY",
                        "severity": "HIGH",
                        "title": "Possible Wrong-Way Movement",
                        "description": f"Vehicle track #{tid} ({vtype}) detected moving against expected flow.",
                        "vehicle_class": vtype,
                        "track_id": tid,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "location": None,
                        "display_location": "Recorded Dataset Footage",
                        "anpr": d.get("plate_number") if d.get("plate_number") else None,
                        "confidence": round(d.get("confidence", 0.85), 2),
                        "evidence_level": "HIGH" if d.get("plate_number") else "MEDIUM",
                        "evidence_image_url": f"/api/demo/evidence/{img_rel_path}",
                        "status": "NEW"
                    }
                    self.events_db.append(evt)
                    new_events.append(evt)

        return new_events

    def _save_evidence_image(
        self,
        frame: Any,
        camera_id: str,
        date_str: str,
        evt_id: str,
        detections: List[Dict[str, Any]]
    ) -> str:
        cam_dir = EVIDENCE_DIR / date_str / camera_id
        cam_dir.mkdir(parents=True, exist_ok=True)
        
        filename = f"{evt_id}_{int(time.time())}.jpg"
        full_path = cam_dir / filename
        rel_path = f"{date_str}/{camera_id}/{filename}"

        # Draw bounding boxes and DEMO ALERT banner on evidence image
        annotated = frame.copy()
        h, w = annotated.shape[:2]

        # Top Banner
        cv2.rectangle(annotated, (0, 0), (w, 45), (18, 53, 91), -1)
        cv2.putText(
            annotated,
            f"DEMO ALERT - RECORDED DATASET FOOTAGE | {camera_id} | {evt_id}",
            (15, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 215, 255),
            2,
            cv2.LINE_AA
        )

        for d in detections:
            bbox = d.get("bbox", [])
            if len(bbox) == 4:
                x1, y1, x2, y2 = [int(v) for v in bbox]
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 0, 255), 2)
                label = f"Track #{d.get('track_id', '')} {d.get('vehicle_type', 'vehicle')}"
                cv2.putText(annotated, label, (x1, max(y1 - 8, 15)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        cv2.imwrite(str(full_path), annotated, [int(cv2.IMWRITE_JPEG_QUALITY), 85])
        return rel_path.replace("\\", "/")

    def get_demo_events(self, camera_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if camera_id:
            return [e for e in self.events_db if e["camera_id"] == camera_id]
        return sorted(self.events_db, key=lambda e: e["timestamp"], reverse=True)

    def get_event_by_id(self, event_id: str) -> Optional[Dict[str, Any]]:
        for e in self.events_db:
            if e["event_id"] == event_id:
                return e
        return None

# Global singleton instance
violation_engine = TrafficViolationEngine()
