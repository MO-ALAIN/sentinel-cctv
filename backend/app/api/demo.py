import os
import cv2
import time
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse, FileResponse, JSONResponse
from app.services.demo_manager import demo_camera_manager
from app.services.traffic_analytics import traffic_analytics_engine
from app.services.violation_detector import violation_engine, EVIDENCE_DIR

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/demo", tags=["VisDrone Demo Mode"])

def gen_demo_mjpeg_stream(camera_id: str):
    """Generates optimized MJPEG multipart frame stream for VisDrone Demo Camera View."""
    worker = demo_camera_manager.get_stream_worker(camera_id)
    if not worker:
        return

    logger.info(f"Started MJPEG demo stream generator for {camera_id}")

    try:
        while True:
            t_loop_start = time.time()
            frame_tuple = worker.get_latest_annotated_frame()
            
            if frame_tuple is not None:
                frame, ts = frame_tuple

                # Resize high-resolution frames (e.g. 4K 3840x2160) to 1280px width for fast 25 FPS web streaming
                h, w = frame.shape[:2]
                if w > 1280:
                    target_w = 1280
                    target_h = int(h * (1280 / w))
                    stream_frame = cv2.resize(frame, (target_w, target_h), interpolation=cv2.INTER_AREA)
                else:
                    stream_frame = frame

                # Encode frame to JPEG
                ret, jpeg = cv2.imencode('.jpg', stream_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ret:
                    frame_bytes = jpeg.tobytes()
                    yield (
                        b'--frame\r\n'
                        b'Content-Type: image/jpeg\r\n'
                        b'Content-Length: ' + str(len(frame_bytes)).encode() + b'\r\n\r\n'
                        + frame_bytes + b'\r\n'
                    )

            # Target ~25 FPS stream delivery (40ms interval)
            elapsed = time.time() - t_loop_start
            sleep_needed = max(0.01, 0.04 - elapsed)
            time.sleep(sleep_needed)

    except GeneratorExit:
        logger.info(f"MJPEG demo stream client disconnected for {camera_id}")

@router.get("/cameras")
def get_demo_cameras():
    """List all available VisDrone MP4 demo cameras."""
    cameras = demo_camera_manager.get_all_cameras()
    return {"cameras": cameras, "count": len(cameras), "mode": "DEMO", "source_type": "DEMO_MP4"}

@router.post("/cameras/{camera_id}/activate")
def activate_demo_scenario(camera_id: str):
    """Activates full GPU inference focus for selected VisDrone demo scenario."""
    success = demo_camera_manager.set_active_scenario(camera_id)
    if not success:
        raise HTTPException(status_code=404, detail=f"Demo camera scenario '{camera_id}' not found.")
    return {"status": "SUCCESS", "active_scenario_id": camera_id}

@router.get("/cameras/{camera_id}")
def get_demo_camera(camera_id: str):
    """Get metadata for a specific demo scenario."""
    cam = demo_camera_manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Demo camera '{camera_id}' not found.")
    return cam

@router.get("/cameras/{camera_id}/health")
def get_demo_camera_health(camera_id: str):
    """Get real-time health telemetry for a specific demo camera."""
    cam = demo_camera_manager.get_camera(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Demo camera '{camera_id}' not found.")
    return cam

@router.get("/cameras/{camera_id}/analytics")
def get_demo_camera_analytics(camera_id: str):
    """Get real-time traffic analytics for specific demo camera."""
    cam_analytics = traffic_analytics_engine.get_camera_analytics(camera_id).get_analytics()
    cam_health = demo_camera_manager.get_camera(camera_id)
    if cam_health:
        cam_analytics["source_type"] = "DEMO_MP4"
        cam_analytics["display_location"] = "Recorded Dataset Footage"
        cam_analytics["name"] = cam_health.get("name")
        cam_analytics["scenario"] = cam_health.get("scenario")
    return cam_analytics

@router.get("/cameras/{camera_id}/annotated")
def get_demo_annotated_stream(camera_id: str):
    """Live MJPEG video stream with YOLO bounding boxes for VisDrone demo camera."""
    demo_camera_manager.set_active_scenario(camera_id)
    worker = demo_camera_manager.get_stream_worker(camera_id)
    if not worker:
        raise HTTPException(status_code=404, detail=f"Demo camera '{camera_id}' stream not available.")
    
    return StreamingResponse(
        gen_demo_mjpeg_stream(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )

@router.get("/cameras/{camera_id}/video")
def get_demo_raw_video(camera_id: str):
    """Serves the raw VisDrone MP4 video file for HTML5 video player playback."""
    worker = demo_camera_manager.get_stream_worker(camera_id)
    if not worker or not os.path.exists(worker.video_path):
        raise HTTPException(status_code=404, detail=f"VisDrone MP4 video file for '{camera_id}' not found.")
    return FileResponse(worker.video_path, media_type="video/mp4")

@router.get("/events")
def get_demo_events(camera_id: str = None):
    """Return list of traffic violation & event alerts generated on demo streams."""
    events = violation_engine.get_demo_events(camera_id=camera_id)
    return {"events": events, "count": len(events), "mode": "DEMO"}

@router.get("/events/{event_id}")
def get_demo_event_detail(event_id: str):
    """Get detailed violation event record by ID."""
    evt = violation_engine.get_event_by_id(event_id)
    if not evt:
        raise HTTPException(status_code=404, detail=f"Demo event '{event_id}' not found.")
    return evt

@router.get("/evidence/{date_str}/{camera_id}/{filename}")
def serve_evidence_image(date_str: str, camera_id: str, filename: str):
    """Serves captured violation evidence image frame."""
    from app.paths import contained_file
    try:
        file_path = contained_file(EVIDENCE_DIR, str(Path(date_str) / camera_id / filename))
    except ValueError:
        raise HTTPException(404,"Evidence not found")
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Evidence image file not found.")
    return FileResponse(str(file_path), media_type="image/jpeg")

@router.get("/quality-report")
def get_demo_quality_report():
    """Return objective non-destructive quality evaluation report for VisDrone dataset."""
    return demo_camera_manager.get_quality_report()
