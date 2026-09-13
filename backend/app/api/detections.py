import cv2
import time
import asyncio
import logging
import numpy as np
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import StreamingResponse
from app.services.stream_manager import stream_manager, StreamCapacityError, StreamBusyError
from app.services.catalogue import catalogue_service
from app.services.yolo_service import yolo_detector

logger = logging.getLogger(__name__)

router = APIRouter(tags=["YOLO Detections"])

def create_status_frame(camera_id: str, status_msg: str = "CONNECTING TO RTSP STREAM...") -> bytes:
    """
    Generate an immediate status frame (1280x720) when RTSP video is connecting or buffering.
    Ensures HTTP 200 OK response and JPEG bytes are sent to browser instantly (< 5ms).
    """
    img = np.zeros((720, 1280, 3), dtype=np.uint8)
    # Fill dark navy background #0F172A
    img[:] = (42, 23, 15)

    # Top header bar
    cv2.rectangle(img, (0, 0), (1280, 60), (30, 41, 59), -1)
    cv2.putText(img, f"SMART CITY Surveillance - Camera: {camera_id.upper()}", (30, 40), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (255, 255, 255), 2, cv2.LINE_AA)

    # Center status message
    cv2.circle(img, (640, 320), 40, (212, 130, 25), -1)
    cv2.putText(img, "CCTV", (615, 328), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2, cv2.LINE_AA)
    
    cv2.putText(img, status_msg, (640 - len(status_msg) * 11, 410), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.9, (226, 232, 240), 2, cv2.LINE_AA)
    
    cv2.putText(img, f"Camera ID: {camera_id} | Stream Standard: RTSP over TCP", (400, 460), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (148, 163, 184), 1, cv2.LINE_AA)

    # Bottom status bar
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    cv2.rectangle(img, (0, 670), (1280, 720), (30, 41, 59), -1)
    cv2.putText(img, f"Status: {status_msg}  |  Timestamp: {now_str}", (30, 700), 
                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (203, 213, 225), 1, cv2.LINE_AA)

    ret, jpeg = cv2.imencode('.jpg', img, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return jpeg.tobytes() if ret else b''

@router.get("/api/detections", response_model=List[Dict[str, Any]])
async def get_recent_detections(
    camera_id: Optional[str] = None,
    vehicle_type: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=500)
):
    """
    PHASE 5 Output API: Return recent real vehicle detections across cameras.
    """
    all_detections: List[Dict[str, Any]] = []
    
    active_ids = stream_manager.get_active_camera_ids()
    target_ids = [camera_id] if camera_id else active_ids

    for cid in target_ids:
        worker = stream_manager.get_worker(cid)
        if worker:
            all_detections.extend(worker.get_recent_detections())

    if vehicle_type:
        vt_clean = vehicle_type.lower()
        all_detections = [d for d in all_detections if d.get("vehicle_type") == vt_clean]

    all_detections.sort(key=lambda d: d.get("timestamp", ""), reverse=True)
    return all_detections[:limit]

@router.get("/api/detections/export")
async def export_detections(request: Request, camera_id: Optional[str] = None):
    from app.api.registry_tools import csv_response
    from app.services.detection_report import detection_row, FIELDS
    from app.services.sighting_repository import sighting_repo
    from app.security import actor
    rows = await get_recent_detections(camera_id=camera_id, vehicle_type=None, limit=500)
    sighting_repo.audit(actor(request)['name'], 'DETECTION_EXPORT', camera_id or 'active cameras')
    response = csv_response([detection_row(d) for d in rows], 'vehicle-detections.csv', FIELDS)
    response.headers['X-Report-Scope'] = 'Recent in-memory detections; at most 100 per camera, 500 total; not a complete recording or accuracy report'
    return response

@router.get("/api/yolo/stats")
async def get_yolo_telemetry():
    """
    Expose YOLO inference performance telemetry (GPU/CPU device, latency, FPS, total detections).
    """
    return yolo_detector.get_telemetry()

async def generate_annotated_mjpeg_frames(camera_id: str):
    """
    Async Generator for browser-compatible MJPEG streaming (Content-Type: multipart/x-mixed-replace; boundary=frame).
    Reuses single backend worker latest annotated frame without opening duplicate RTSP connections.
    Instantly sends an initial JPEG frame so HTTP response headers open immediately in browser (< 5ms).
    """
    worker = stream_manager.get_worker(camera_id)
    # Admission happens before StreamingResponse headers are sent.

    if worker:
        worker.stream_clients += 1
        logger.info(f"[{camera_id.upper()}] MJPEG Client Connected: SUCCESS (Active Clients: {worker.stream_clients})")

    # Send immediate initial status frame so HTTP headers open in browser without delay
    initial_status_jpg = create_status_frame(camera_id, "CONNECTING TO LIVE CCTV...")
    if initial_status_jpg:
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + initial_status_jpg + b'\r\n')

    try:
        while True:
            worker = stream_manager.get_worker(camera_id)
            if not worker or worker._stop_event.is_set():
                break

            frame_data = worker.get_latest_annotated_frame()
            if frame_data is not None:
                frame, _ = frame_data
                ret, jpeg = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                if ret:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n')
            else:
                # If buffering or connecting, yield status frame to keep stream active
                status_msg = f"RTSP STATUS: {worker.status.upper()}" if worker else "CONNECTING..."
                status_jpg = create_status_frame(camera_id, status_msg)
                if status_jpg:
                    yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + status_jpg + b'\r\n')

            await asyncio.sleep(0.04)

    except asyncio.CancelledError:
        logger.info(f"[{camera_id.upper()}] MJPEG Stream Client disconnected.")
    except Exception as ex:
        logger.error(f"[{camera_id.upper()}] Stream Generator Error: {ex}")
    finally:
        if worker:
            worker.stream_clients = max(0, worker.stream_clients - 1)
            logger.info(f"[{camera_id.upper()}] Client Disconnected (Remaining Clients: {worker.stream_clients})")

@router.get("/api/cameras/{camera_id}/annotated")
async def annotated_mjpeg_stream(camera_id: str):
    """
    Visual Stream: Live MJPEG stream displaying YOLO + ByteTrack annotated frames.
    """
    worker = stream_manager.get_worker(camera_id)
    if not worker or worker.status in ("DISCONNECTED", "ERROR"):
        cam = await catalogue_service.get_camera_by_id(camera_id)
        if not cam:
            raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' not found in catalogue.")
        try:
            worker = stream_manager.start_camera(camera_id, cam["rtsp_url"])
        except (StreamCapacityError, StreamBusyError) as error:
            raise HTTPException(409, str(error)) from error

    return StreamingResponse(
        generate_annotated_mjpeg_frames(camera_id),
        media_type="multipart/x-mixed-replace; boundary=frame"
    )
