import os
import cv2
import time
import threading
import logging
from collections import deque
from typing import Optional, Tuple, Dict, Any, List
from app.config import get_settings
from app.services.yolo_service import yolo_detector

logger = logging.getLogger(__name__)

# Force TCP and 2s timeout for RTSP stability in ffmpeg backend
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp|stimeout;2000000"

class RTSPStreamWorker:
    def __init__(self, camera_id: str, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.settings = get_settings()
        
        # Stream metrics
        self.status = "DISCONNECTED"  # CONNECTING, CONNECTED, RECONNECTING, DISCONNECTED, ERROR
        self.fps = 0.0
        self.frames_received = 0
        self.last_frame_timestamp: Optional[float] = None
        self.resolution: Tuple[int, int] = (0, 0)
        self.error_message: Optional[str] = None
        self.stream_clients: int = 0
        
        # Bounded frame buffer (maxlen=2 ensures zero lag backlog & no memory leaks)
        self._raw_frame_buffer = deque(maxlen=2)
        self._annotated_frame_buffer = deque(maxlen=2)
        self._buffer_lock = threading.RLock()
        
        # Recent vehicle detections for this camera (bounded maxlen=100)
        self.recent_detections = deque(maxlen=100)
        
        # Worker control
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        
        # FPS calculation window
        self._fps_window = deque(maxlen=30)
        self._frame_counter = 0

    def get_health(self) -> Dict[str, Any]:
        """Task 12: Camera Health Telemetry Endpoint data provider."""
        now = time.time()
        age_ms = int((now - self.last_frame_timestamp) * 1000.0) if self.last_frame_timestamp else None
        is_streaming = self.is_frame_delivery_active(max_stale_seconds=5.0)

        if is_streaming:
            conn_state = "CONNECTED"
        elif self.status == "CONNECTING":
            conn_state = "CONNECTING"
        elif self.status == "RECONNECTING":
            conn_state = "RECONNECTING"
        elif self.status in ("ENDED", "ERROR", "DISCONNECTED"):
            conn_state = self.status
        else:
            conn_state = "FRAME_DELIVERY_ERROR"

        return {
            "camera_id": self.camera_id,
            "connection": conn_state,
            "streaming": is_streaming,
            "frames_received": self.frames_received,
            "fps": round(self.fps, 1),
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}" if self.resolution != (0, 0) else "N/A",
            "last_frame_age_ms": age_ms,
            "gpu": yolo_detector.device_name,
            "cuda": yolo_detector.cuda_available,
            "error": self.error_message
        }

    def start(self):
        """Start the background stream ingestion thread."""
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"[{self.camera_id}] Worker thread already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"RTSPWorker-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info(f"[{self.camera_id}] Worker thread started")

    def stop(self):
        """Stop the background stream ingestion thread."""
        logger.info(f"[{self.camera_id}] Stopping worker thread...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=15.0)
            if self._thread.is_alive():
                raise RuntimeError('Worker is still stopping; retry after current decoding/inference completes')
        self.status = "DISCONNECTED"
        logger.info(f"[{self.camera_id}] Worker thread stopped.")

    def get_latest_frame(self) -> Optional[Tuple[Any, float]]:
        """Retrieve the latest raw BGR frame and timestamp without blocking."""
        with self._buffer_lock:
            if not self._raw_frame_buffer:
                return None
            return self._raw_frame_buffer[-1]

    def get_latest_annotated_frame(self) -> Optional[Tuple[Any, float]]:
        """Retrieve the latest YOLO annotated frame and timestamp without blocking."""
        with self._buffer_lock:
            if not self._annotated_frame_buffer:
                return self.get_latest_frame()
            return self._annotated_frame_buffer[-1]

    def get_recent_detections(self) -> List[Dict[str, Any]]:
        with self._buffer_lock:
            return list(self.recent_detections)

    def is_frame_delivery_active(self, max_stale_seconds: float = 5.0) -> bool:
        """
        Step 8: Heartbeat Check.
        Returns True ONLY if stream is CONNECTED and a frame was received within max_stale_seconds.
        """
        if self.status != "CONNECTED" or self.last_frame_timestamp is None:
            return False
        return (time.time() - self.last_frame_timestamp) <= max_stale_seconds

    def get_status(self) -> Dict[str, Any]:
        """Return real-time stream status and telemetry metrics."""
        is_active = self.is_frame_delivery_active(max_stale_seconds=5.0)
        has_frame = len(self._annotated_frame_buffer) > 0 or len(self._raw_frame_buffer) > 0
        
        # Determine strict camera connection status for frontend
        if is_active:
            effective_status = "CONNECTED"
        elif self.status == "CONNECTING":
            effective_status = "CONNECTING"
        elif self.status == "RECONNECTING":
            effective_status = "RECONNECTING"
        elif self.status in ("ERROR", "DISCONNECTED", "ENDED"):
            effective_status = self.status
        else:
            effective_status = "FRAME_DELIVERY_ERROR"

        return {
            "camera_id": self.camera_id,
            "rtsp_status": self.status,
            "status": effective_status,
            "is_frame_delivery_active": is_active,
            "worker_running": self._thread is not None and self._thread.is_alive(),
            "frames_received": self.frames_received,
            "latest_frame_available": has_frame,
            "yolo_processing": yolo_detector.model is not None,
            "stream_clients": self.stream_clients,
            "fps": round(self.fps, 2),
            "last_frame_timestamp": self.last_frame_timestamp,
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}" if self.resolution != (0, 0) else "N/A",
            "error_message": self.error_message,
            "rtsp_url": "[configured]",
            "recent_detections_count": len(self.recent_detections)
        }

    def _run_loop(self):
        from datetime import datetime
        from app.services.frame_clock import FrameClock, SceneBoundary
        from app.services.sighting_repository import sighting_repo
        from app.services.traffic_analytics import traffic_analytics_engine
        from app.services.incident_detector import incident_engine
        metadata = sighting_repo.get_camera(self.camera_id) or {}
        recorded = metadata.get('source_type') == 'RECORDED'
        retry_delay = 2.0
        while not self._stop_event.is_set():
            self.status = 'CONNECTING'
            params = [cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000]
            cap = cv2.VideoCapture(self.rtsp_url) if recorded else cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG, params)
            if not cap.isOpened():
                cap.release()
                self.status = 'ERROR'
                self.error_message = 'Source unavailable; check file, network and authorized credentials'
                if recorded: return
                self._stop_event.wait(retry_delay)
                retry_delay = min(30, retry_delay * 2)
                continue
            yolo_detector.reset_camera(self.camera_id)
            traffic_analytics_engine.reset_camera_tracking(self.camera_id)
            incident_engine.reset_camera(self.camera_id)
            frame_clock = FrameClock(metadata.get('recording_started_at'))
            scene_boundary = SceneBoundary()
            decode_failures = 0
            connection_frames = 0
            playback_anchor = None
            first_pts = None
            self.error_message = None
            try:
                while not self._stop_event.is_set():
                    ok, frame = cap.read()
                    if not ok or frame is None:
                        self.status = 'ENDED' if recorded else 'RECONNECTING'
                        if recorded: return
                        decode_failures += 1
                        if decode_failures < 3:
                            self._stop_event.wait(.1)
                            continue
                        self.error_message = 'Stream interrupted; reconnecting'
                        break
                    decode_failures = 0
                    connection_frames += 1
                    if connection_frames >= 30: retry_delay = 2
                    timing = frame_clock.observe(cap.get(cv2.CAP_PROP_POS_MSEC))
                    cut = scene_boundary.observe(frame)
                    if timing and (timing['discontinuity'] or cut or timing['delta_seconds'] > self.settings.TRACK_INACTIVE_TIMEOUT_SECONDS):
                        yolo_detector.reset_camera(self.camera_id)
                        traffic_analytics_engine.reset_camera_tracking(self.camera_id)
                        incident_engine.reset_camera(self.camera_id)
                        playback_anchor = None
                    if recorded and timing:
                        if playback_anchor is None:
                            playback_anchor, first_pts = time.monotonic(), timing['pts_seconds']
                        self._stop_event.wait(max(0,playback_anchor+timing['pts_seconds']-first_pts-time.monotonic()))
                        if self._stop_event.is_set(): break
                    now = time.time()
                    self.status = 'CONNECTED'
                    self.frames_received += 1
                    self._frame_counter += 1
                    self.last_frame_timestamp = now
                    self.resolution = (frame.shape[1], frame.shape[0])
                    self._fps_window.append(now)
                    if len(self._fps_window) > 1:
                        self.fps = (len(self._fps_window)-1) / max(.001, now-self._fps_window[0])
                    annotated = frame
                    with self._buffer_lock:
                        self._raw_frame_buffer.append((frame,now))
                    if timing is None:
                        self.error_message = 'Video available; analytics waiting for advancing media timestamps'
                    elif self.error_message == 'Video available; analytics waiting for advancing media timestamps':
                        self.error_message = None
                    if timing and self._frame_counter % max(1,self.settings.YOLO_FRAME_INTERVAL) == 0 and yolo_detector.model is not None:
                        try:
                            result = yolo_detector.track_vehicles(frame,self.camera_id,timestamp=timing['timestamp'],media_offset_seconds=timing['pts_seconds'],timestamp_basis=timing['timestamp_basis'])
                            if self.error_message and self.error_message.startswith('Video available; analytics failed:'):
                                self.error_message = None
                            annotated = result['annotated_frame']
                            dets = result['detections']
                            for detection in dets:
                                detection['source_type'] = metadata.get('source_type','UNKNOWN')
                                detection['source_system'] = metadata.get('source_system','')
                                detection['camera_name'] = metadata.get('name',self.camera_id)
                                detection['location'] = metadata.get('location','')
                            analytics = result.get('analytics') or traffic_analytics_engine.get_camera_analytics(self.camera_id).get_analytics()
                            incident_engine.evaluate_frame_events(self.camera_id, traffic_analytics_engine.get_camera_analytics(self.camera_id).active_tracks, analytics.get('traffic_density','LOW'),current_time=datetime.fromisoformat(timing['timestamp']).timestamp())
                            with self._buffer_lock:
                                self.recent_detections.extend(dets)
                        except Exception as exc:
                            self.error_message = 'Video available; analytics failed: ' + type(exc).__name__
                            logger.exception('Inference failed for %s',self.camera_id)
                    source_label = metadata.get('source_type','UNKNOWN')
                    cv2.putText(annotated,source_label,(10,annotated.shape[0]-12),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,200,255),2)
                    with self._buffer_lock:
                        self._annotated_frame_buffer.append((annotated,now))
            finally:
                cap.release()
            self._stop_event.wait(retry_delay)
            retry_delay = min(30,retry_delay*2)
        self.status = 'DISCONNECTED'
