import logging
import threading
from typing import Dict, Optional, Any, List
from app.services.stream_worker import RTSPStreamWorker
from app.config import get_settings

logger = logging.getLogger(__name__)

class StreamCapacityError(RuntimeError):
    pass


class StreamBusyError(RuntimeError):
    pass


class MultiCameraStreamManager:
    def __init__(self):
        self._workers: Dict[str, RTSPStreamWorker] = {}
        self._lock = threading.Lock()
        self._stopping = set()
        self._shutting_down = False
        self.max_active_cameras = get_settings().MAX_ACTIVE_CAMERAS

    def get_worker(self, camera_id: str) -> Optional[RTSPStreamWorker]:
        with self._lock:
            return self._workers.get(camera_id)

    def start_camera(self, camera_id: str, rtsp_url: str) -> RTSPStreamWorker:
        """Start an independent worker for a camera if not already running."""
        with self._lock:
            if self._shutting_down or camera_id in self._stopping:
                raise StreamBusyError("Camera is stopping. Wait for it to finish before reconnecting.")
            worker = self._workers.get(camera_id)
            if worker is not None and worker._thread and worker._thread.is_alive():
                if getattr(worker, "_stop_event", None) and worker._stop_event.is_set():
                    raise StreamBusyError("Camera is still stopping. Wait before reconnecting.")
                return worker
            running = sum(cid in self._stopping or bool(w._thread and w._thread.is_alive()) for cid, w in self._workers.items())
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
        """Wait for one worker without holding the shared camera registry lock."""
        with self._lock:
            worker = self._workers.get(camera_id)
            if worker is None:
                return False
            if camera_id in self._stopping:
                raise StreamBusyError("Camera is already stopping. Please wait before retrying.")
            self._stopping.add(camera_id)
        stopped = False
        try:
            worker.stop()
            stopped = True
            logger.info("Stream Manager: Stopped worker for %s", camera_id)
            return True
        except RuntimeError as error:
            # Keep a still-running worker registered and counted; never replace it.
            raise StreamBusyError("Camera is still stopping. Retry after the current video operation finishes.") from error
        finally:
            with self._lock:
                if stopped:
                    self._workers.pop(camera_id, None)
                self._stopping.discard(camera_id)

    def stop_all(self):
        """Prevent new starts and attempt every worker even if one cannot stop."""
        with self._lock:
            self._shutting_down = True
            camera_ids = list(self._workers)
        for camera_id in camera_ids:
            try:
                self.stop_camera(camera_id)
            except StreamBusyError:
                logger.warning("Worker %s is still stopping during shutdown", camera_id)

    def get_capacity(self):
        with self._lock:
            active = sum(cid in self._stopping or bool(w._thread and w._thread.is_alive()) for cid, w in self._workers.items())
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
