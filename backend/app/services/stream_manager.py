import logging
import threading
from typing import Dict, Optional, Any, List
from app.services.stream_worker import RTSPStreamWorker
from app.config import get_settings

logger = logging.getLogger(__name__)

class StreamCapacityError(RuntimeError):
    pass


class MultiCameraStreamManager:
    def __init__(self):
        self._workers: Dict[str, RTSPStreamWorker] = {}
        self._lock = threading.Lock()
        self.max_active_cameras = get_settings().MAX_ACTIVE_CAMERAS

    def get_worker(self, camera_id: str) -> Optional[RTSPStreamWorker]:
        with self._lock:
            return self._workers.get(camera_id)

    def start_camera(self, camera_id: str, rtsp_url: str) -> RTSPStreamWorker:
        """Start an independent worker for a camera if not already running."""
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker is not None and worker._thread and worker._thread.is_alive():
                return worker
            running = sum(bool(w._thread and w._thread.is_alive()) for w in self._workers.values())
            if running >= self.max_active_cameras:
                raise StreamCapacityError(
                    f"Camera limit reached ({self.max_active_cameras}). Disconnect another camera before connecting this one.")
            created = worker is None
            if created:
                worker = RTSPStreamWorker(camera_id=camera_id, rtsp_url=rtsp_url)
                self._workers[camera_id] = worker
            else:
                worker.rtsp_url = rtsp_url
            try:
                worker.start()
            except Exception:
                if created:
                    self._workers.pop(camera_id, None)
                raise
            logger.info("Stream Manager: Started worker for %s", camera_id)
            return worker

    def stop_camera(self, camera_id: str) -> bool:
        """Stop an independent camera worker without affecting others."""
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker:
                worker.stop()
                self._workers.pop(camera_id, None)
                logger.info(f"Stream Manager: Stopped worker for {camera_id}")
                return True
            return False

    def stop_all(self):
        """Stop all active camera workers."""
        with self._lock:
            for cam_id, worker in list(self._workers.items()):
                logger.info(f"Stream Manager: Shutting down worker for {cam_id}")
                worker.stop()
            self._workers.clear()

    def get_capacity(self):
        with self._lock:
            active = sum(bool(w._thread and w._thread.is_alive()) for w in self._workers.values())
            return {"active_workers": active, "max_active_cameras": self.max_active_cameras,
                    "available_slots": max(0, self.max_active_cameras-active)}

    def get_active_camera_ids(self) -> List[str]:
        with self._lock:
            return list(self._workers.keys())

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {cam_id: worker.get_status() for cam_id, worker in self._workers.items()}

# Global singleton instance
stream_manager = MultiCameraStreamManager()
