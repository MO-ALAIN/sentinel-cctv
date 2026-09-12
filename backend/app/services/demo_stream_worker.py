import os
import cv2
import time
import threading
import logging
from collections import deque
from typing import Optional, Tuple, Dict, Any, List
from app.services.yolo_service import yolo_detector
from app.services.traffic_analytics import traffic_analytics_engine
from app.services.incident_detector import incident_engine
from app.services.violation_detector import violation_engine

logger = logging.getLogger(__name__)

class DemoStreamWorker:
    def __init__(
        self,
        camera_id: str,
        video_path: str,
        name: str,
        scenario: str,
        camera_type: str,
        anpr_capability: str,
        fps: int = 25
    ):
        self.camera_id = camera_id
        self.video_path = video_path
        self.name = name
        self.scenario = scenario
        self.type = camera_type
        self.anpr_capability = anpr_capability
        self.target_fps = fps
        self.frame_delay = 1.0 / fps

        # Focus state: Active scenario gets full 25 FPS pipeline; non-active scenarios run lightweight background sampling
        self.is_active_focus = (camera_id == "CAM-DEMO-01")

        # Worker status & metrics
        self.status = "READY"  # PLAYING, READY, ERROR
        self.fps_actual = 0.0
        self.frames_received = 0
        self.last_frame_timestamp: Optional[float] = None
        self.resolution: Tuple[int, int] = (0, 0)
        self.error_message: Optional[str] = None

        # Buffers (maxlen=2 to avoid lag & memory accumulation)
        self._raw_frame_buffer = deque(maxlen=2)
        self._annotated_frame_buffer = deque(maxlen=2)
        self._buffer_lock = threading.RLock()

        self.recent_detections = deque(maxlen=100)

        # Worker thread control
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # FPS stats
        self._fps_window = deque(maxlen=30)
        self._frame_counter = 0

    def set_active_focus(self, is_active: bool):
        self.is_active_focus = is_active

    def start(self):
        if self._thread is not None and self._thread.is_alive():
            logger.warning(f"[{self.camera_id}] Demo worker thread already running.")
            return

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop, name=f"DemoWorker-{self.camera_id}", daemon=True)
        self._thread.start()
        logger.info(f"[{self.camera_id}] VisDrone MP4 demo worker started: {self.video_path}")

    def stop(self):
        logger.info(f"[{self.camera_id}] Stopping demo worker...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=3.0)
        self.status = "READY"
        logger.info(f"[{self.camera_id}] Demo worker stopped.")

    def get_latest_frame(self) -> Optional[Tuple[Any, float]]:
        with self._buffer_lock:
            if not self._raw_frame_buffer:
                return None
            return self._raw_frame_buffer[-1]

    def get_latest_annotated_frame(self) -> Optional[Tuple[Any, float]]:
        with self._buffer_lock:
            if not self._annotated_frame_buffer:
                return self.get_latest_frame()
            return self._annotated_frame_buffer[-1]

    def get_recent_detections(self) -> List[Dict[str, Any]]:
        with self._buffer_lock:
            return list(self.recent_detections)

    def get_health(self) -> Dict[str, Any]:
        now = time.time()
        age_ms = int((now - self.last_frame_timestamp) * 1000.0) if self.last_frame_timestamp else None
        
        # Pull live traffic stats for this camera
        analytics = traffic_analytics_engine.get_camera_analytics(self.camera_id).get_analytics()
        active_vehicles = analytics.get("active_vehicles", 0)
        unique_vehicles = analytics.get("total_unique_vehicles", 0)
        traffic_density = analytics.get("traffic_density", "LOW")

        return {
            "camera_id": self.camera_id,
            "id": self.camera_id,
            "source_type": "DEMO_MP4",
            "name": self.name,
            "scenario": self.scenario,
            "type": self.type,
            "anpr_capability": self.anpr_capability,
            "source": "VisDrone Dataset",
            "mode": "DEMO",
            "recorded": True,
            "location": None,
            "display_location": "Recorded Dataset Footage",
            "status": self.status,
            "video_source": os.path.basename(self.video_path),
            "video_file": os.path.basename(self.video_path),
            "frames_received": self.frames_received,
            "fps": round(self.fps_actual, 1),
            "resolution": f"{self.resolution[0]}x{self.resolution[1]}" if self.resolution != (0, 0) else "N/A",
            "last_frame_age_ms": age_ms,
            "gpu": yolo_detector.device_name,
            "cuda": yolo_detector.cuda_available,
            "active_vehicles": active_vehicles,
            "total_unique_vehicles": unique_vehicles,
            "traffic_density": traffic_density,
            "is_active_focus": self.is_active_focus,
            "error": self.error_message
        }

    def _run_loop(self):
        if not os.path.exists(self.video_path):
            self.error_message = f"VisDrone MP4 file not found: {self.video_path}"
            self.status = "ERROR"
            logger.error(f"[{self.camera_id}] {self.error_message}")
            return

        cap = cv2.VideoCapture(self.video_path)
        if not cap.isOpened():
            self.error_message = f"Failed to open VisDrone MP4 video: {self.video_path}"
            self.status = "ERROR"
            logger.error(f"[{self.camera_id}] {self.error_message}")
            return

        self.status = "PLAYING"
        self.error_message = None
        logger.info(f"[{self.camera_id}] Streaming VisDrone MP4 video: {self.video_path}")

        while not self._stop_event.is_set():
            t_start = time.time()

            # Lightweight throttling for non-focused demo scenarios to save GPU VRAM/compute
            if not self.is_active_focus and self._frame_counter % 3 != 0:
                time.sleep(0.04)

            ret, frame = cap.read()

            if not ret or frame is None:
                # Video loop reached end: Smooth reset to frame 0 and reset tracking session
                logger.info(f"[{self.camera_id}] Video EOF reached. Looping back to start & resetting session state.")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                traffic_analytics_engine.reset_camera_tracking(self.camera_id)
                yolo_detector.reset_camera(self.camera_id)
                ret, frame = cap.read()
                if not ret or frame is None:
                    time.sleep(0.1)
                    continue

            now = time.time()
            self.frames_received += 1
            self._frame_counter += 1
            self.last_frame_timestamp = now

            if self.resolution == (0, 0):
                h, w = frame.shape[:2]
                self.resolution = (w, h)

            self._fps_window.append(now)
            if len(self._fps_window) > 1:
                time_diff = self._fps_window[-1] - self._fps_window[0]
                if time_diff > 0:
                    self.fps_actual = (len(self._fps_window) - 1) / time_diff

            # Raw frame buffer
            with self._buffer_lock:
                self._raw_frame_buffer.append((frame.copy(), now))

            # Frame Sampling for YOLO Inference (Active focus runs 25 FPS inference; non-focused runs lightweight sampling)
            should_infer = self.is_active_focus or (self._frame_counter % 10 == 0) or len(self._annotated_frame_buffer) == 0

            if should_infer:
                try:
                    yolo_res = yolo_detector.track_vehicles(frame, self.camera_id)
                    annotated = yolo_res["annotated_frame"]
                    dets = yolo_res["detections"]

                    # Update Traffic Analytics Engine
                    analytics_data = yolo_res.get("analytics") or traffic_analytics_engine.get_camera_analytics(self.camera_id).get_analytics()

                    # Process Incident & Violation Detector rules
                    active_trks = traffic_analytics_engine.get_camera_analytics(self.camera_id).active_tracks
                    incident_engine.evaluate_frame_events(
                        camera_id=self.camera_id,
                        active_tracks=active_trks,
                        traffic_density=analytics_data.get("traffic_density", "LOW")
                    )

                    # Process Violation Engine (Captures sharp evidence frames on traffic events)
                    violation_engine.process_demo_frame(self.camera_id, frame, dets, analytics_data)

                    with self._buffer_lock:
                        self._annotated_frame_buffer.append((annotated, now))
                        for d in dets:
                            self.recent_detections.append(d)

                except Exception as ex:
                    logger.error(f"[{self.camera_id}] VisDrone frame inference error: {ex}")
                    with self._buffer_lock:
                        self._annotated_frame_buffer.append((frame.copy(), now))
            else:
                # Use latest annotated frame or raw frame for smooth stream continuity
                latest_annotated = self._annotated_frame_buffer[-1][0] if self._annotated_frame_buffer else frame
                with self._buffer_lock:
                    self._annotated_frame_buffer.append((latest_annotated, now))

            # Throttle loop to target FPS (~25 FPS = ~40ms per frame)
            t_elapsed = time.time() - t_start
            sleep_time = self.frame_delay - t_elapsed
            if sleep_time > 0:
                time.sleep(sleep_time)

        cap.release()
        self.status = "READY"
