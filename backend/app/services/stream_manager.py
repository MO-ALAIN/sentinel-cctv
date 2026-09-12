import logging
import threading
from typing import Dict, Optional, Any, List
from app.services.stream_worker import RTSPStreamWorker

logger = logging.getLogger(__name__)

class MultiCameraStreamManager:
    def __init__(self):
        self._workers: Dict[str, RTSPStreamWorker] = {}
        self._lock = threading.Lock()

    def get_worker(self, camera_id: str) -> Optional[RTSPStreamWorker]:
        with self._lock:
            return self._workers.get(camera_id)

    def start_camera(self, camera_id: str, rtsp_url: str) -> RTSPStreamWorker:
        """Start an independent worker for a camera if not already running."""
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker is None:
                worker = RTSPStreamWorker(camera_id=camera_id, rtsp_url=rtsp_url)
                self._workers[camera_id] = worker
                worker.start()
                logger.info(f"Stream Manager: Started worker for {camera_id}")
            elif worker.status in ("DISCONNECTED", "ERROR", "ENDED") or not worker._thread or not worker._thread.is_alive():
                worker.rtsp_url = rtsp_url
                worker.start()
                logger.info(f"Stream Manager: Restarted worker for {camera_id}")
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

    def get_active_camera_ids(self) -> List[str]:
        with self._lock:
            return list(self._workers.keys())

    def get_all_statuses(self) -> Dict[str, Dict[str, Any]]:
        with self._lock:
            return {cam_id: worker.get_status() for cam_id, worker in self._workers.items()}

# Global singleton instance
stream_manager = MultiCameraStreamManager()
