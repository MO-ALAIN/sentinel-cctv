import time
import logging
import threading
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from app.config import get_settings

logger = logging.getLogger(__name__)

class VehicleTrack:
    """
    Represents a single ByteTrack vehicle track history.
    Implements Temporal Class Voting to eliminate per-frame class flickering.
    """
    def __init__(self, camera_id: str, track_id: int, vehicle_type: str, confidence: float, bbox: List[int], timestamp: str):
        self.camera_id = camera_id
        self.track_id = track_id
        self.latest_bbox = bbox
        self.first_seen_timestamp = timestamp
        self.last_seen_timestamp = timestamp
        self.last_seen_epoch = time.time()
        self.detection_count = 1
        self.status = "ACTIVE"  # ACTIVE or INACTIVE

        # Temporal Voting per track across frames
        self.class_votes: Dict[str, int] = {vehicle_type: 1}
        self.confidence_sum: Dict[str, float] = {vehicle_type: confidence}
        self.vehicle_type = vehicle_type
        self.confidence = confidence

    def update(self, vehicle_type: str, confidence: float, bbox: List[int], timestamp: str):
        self.latest_bbox = bbox
        self.last_seen_timestamp = timestamp
        self.last_seen_epoch = time.time()
        self.detection_count += 1
        self.status = "ACTIVE"

        # Record temporal vote
        self.class_votes[vehicle_type] = self.class_votes.get(vehicle_type, 0) + 1
        self.confidence_sum[vehicle_type] = self.confidence_sum.get(vehicle_type, 0.0) + confidence

        # Majority voting for stable track classification
        stable_type = max(self.class_votes, key=self.class_votes.get)
        self.vehicle_type = stable_type
        self.confidence = self.confidence_sum[stable_type] / float(self.class_votes[stable_type])

    def to_dict(self) -> Dict[str, Any]:
        return {
            "camera_id": self.camera_id,
            "track_id": self.track_id,
            "vehicle_type": self.vehicle_type,
            "confidence": round(self.confidence, 3),
            "bbox": self.latest_bbox,
            "first_seen_timestamp": self.first_seen_timestamp,
            "last_seen_timestamp": self.last_seen_timestamp,
            "detection_count": self.detection_count,
            "class_votes": dict(self.class_votes),
            "status": self.status
        }

class MultiCameraTrackManager:
    """
    Manages vehicle tracks per camera independently.
    Handles track lifecycle, persistence, and auto-deactivation timeouts.
    """
    def __init__(self):
        self.settings = get_settings()
        self._tracks: Dict[str, Dict[int, VehicleTrack]] = {}
        self._lock = threading.Lock()

    def update_track(
        self,
        camera_id: str,
        track_id: int,
        vehicle_type: str,
        confidence: float,
        bbox: List[int],
        timestamp: Optional[str] = None
    ) -> VehicleTrack:
        if timestamp is None:
            timestamp = datetime.now(timezone.utc).isoformat()

        with self._lock:
            if camera_id not in self._tracks:
                self._tracks[camera_id] = {}

            cam_tracks = self._tracks[camera_id]
            if track_id in cam_tracks:
                track = cam_tracks[track_id]
                track.update(vehicle_type, confidence, bbox, timestamp)
            else:
                track = VehicleTrack(camera_id, track_id, vehicle_type, confidence, bbox, timestamp)
                cam_tracks[track_id] = track
                logger.info(f"[{camera_id}] New vehicle track spawned: Track #{track_id} ({vehicle_type})")

            return track

    def refresh_track_statuses(self):
        """Mark tracks as INACTIVE if not seen within the timeout window."""
        timeout = self.settings.TRACK_INACTIVE_TIMEOUT_SECONDS
        now = time.time()
        with self._lock:
            for cam_id, cam_tracks in self._tracks.items():
                for track in cam_tracks.values():
                    if track.status == "ACTIVE" and (now - track.last_seen_epoch) > timeout:
                        track.status = "INACTIVE"
                        logger.info(f"[{cam_id}] Track #{track.track_id} marked INACTIVE (Last seen {now - track.last_seen_epoch:.1f}s ago).")

    def get_tracks(self, camera_id: Optional[str] = None, status_filter: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
        self.refresh_track_statuses()
        results = []
        with self._lock:
            target_cams = [camera_id] if camera_id else list(self._tracks.keys())
            for cid in target_cams:
                cam_tracks = self._tracks.get(cid, {})
                for track in cam_tracks.values():
                    if status_filter and track.status.upper() != status_filter.upper():
                        continue
                    results.append(track.to_dict())

        # Sort by last seen timestamp descending
        results.sort(key=lambda t: t["last_seen_timestamp"], reverse=True)
        return results[:limit]

    def get_camera_tracks(self, camera_id: str) -> List[Dict[str, Any]]:
        return self.get_tracks(camera_id=camera_id)

    def get_summary_stats(self) -> Dict[str, Any]:
        self.refresh_track_statuses()
        total_unique = 0
        total_active = 0
        per_camera_summary = {}

        with self._lock:
            for cam_id, cam_tracks in self._tracks.items():
                cam_total = len(cam_tracks)
                cam_active = sum(1 for t in cam_tracks.values() if t.status == "ACTIVE")
                total_unique += cam_total
                total_active += cam_active
                per_camera_summary[cam_id] = {
                    "total_tracks": cam_total,
                    "active_tracks": cam_active
                }

        return {
            "total_unique_tracks": total_unique,
            "total_active_tracks": total_active,
            "cameras": per_camera_summary
        }

# Global singleton instance
track_manager = MultiCameraTrackManager()
