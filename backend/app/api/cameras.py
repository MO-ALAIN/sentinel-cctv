import cv2
import asyncio
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Query, Request
from app.security import require_role, actor
from app.services.sighting_repository import sighting_repo
from app.api.registry_tools import public_camera
from fastapi.responses import StreamingResponse, Response
from app.services.catalogue import catalogue_service
from app.services.stream_manager import stream_manager
from app.services.anpr_assessor import anpr_assessor
from app.services.anpr_diagnostic import anpr_diagnostic_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/cameras", tags=["Cameras"])

# =====================================================================
# PHASE 7.7 ANPR DIAGNOSTIC REST APIs
# =====================================================================

@router.get("/anpr-diagnostic")
async def get_anpr_diagnostic():
    """
    PHASE 7.7 API: Return latest government CCTV ANPR diagnostic and real camera validation results.
    """
    if anpr_diagnostic_service.latest_diagnostics:
        return {
            "status": "COMPLETED",
            "total_cameras": len(anpr_diagnostic_service.latest_diagnostics),
            "results": list(anpr_diagnostic_service.latest_diagnostics.values())
        }
    
    summary = await anpr_diagnostic_service.run_diagnostics_selected(
        camera_ids=["cam15", "cam16", "cam06", "cam04", "cam05"],
        duration_per_camera=15
    )
    return summary

@router.get("/anpr-diagnostic/{camera_id}")
async def get_camera_anpr_diagnostic(camera_id: str):
    """
    Return detailed Phase 7.7 ANPR diagnostic results for a specific camera.
    """
    latest = anpr_diagnostic_service.latest_diagnostics
    if camera_id in latest:
        return latest[camera_id]

    cam = await catalogue_service.get_camera_by_id(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found.")

    res = await anpr_diagnostic_service.diagnose_camera(cam, duration_seconds=15)
    return res

@router.post("/anpr-diagnostic/run")
async def run_anpr_diagnostic_job(
    duration: int = Query(default=20, ge=10, le=120, description="Duration in seconds per camera"),
    camera_id: Optional[str] = Query(default=None, description="Optional single camera ID to diagnose")
):
    """
    Trigger a fresh Phase 7.7 ANPR diagnostic job on government cameras.
    """
    if anpr_diagnostic_service.is_running:
        return {
            "status": "RUNNING",
            "message": "ANPR diagnostic job is already running in background."
        }

    cams = [camera_id] if camera_id else ["cam15", "cam16", "cam06", "cam04", "cam05"]
    summary = await anpr_diagnostic_service.run_diagnostics_selected(
        camera_ids=cams,
        duration_per_camera=duration
    )
    return summary

# =====================================================================
# PHASE 7.6 ANPR ASSESSMENT APIs
# =====================================================================

@router.get("/anpr-status")
async def get_all_anpr_statuses():
    """
    PHASE 11 API: Return intelligent ANPR capability statuses across all cameras.
    Statuses: ANPR_READY, ANPR_POTENTIAL, ANPR_LIMITED, ANPR_UNSUITABLE.
    """
    from app.services.anpr_status_engine import anpr_status_engine
    assessment = anpr_assessor.latest_assessment
    if not assessment:
        assessment = {"results": []}

    results = assessment.get("results", [])
    statuses = []
    for r in results:
        cid = r["camera_id"]
        status_info = anpr_status_engine.evaluate_camera_anpr_status(
            camera_id=cid,
            plate_candidates_count=r.get("plate_candidates", 0),
            best_resolution_px=r.get("best_plate_height", 0),
            best_quality_score=r.get("anpr_score", 0.0),
            ocr_attempts_count=r.get("ocr_attempts", 0),
            confirmed_plates_count=r.get("ocr_successes", 0)
        )
        status_info["camera_name"] = r.get("camera_name", cid)
        statuses.append(status_info)

    return {
        "status": "COMPLETED",
        "total_cameras": len(statuses),
        "cameras": statuses
    }

@router.get("/anpr-assessment")
async def get_anpr_assessment():
    """
    PHASE 7.6 API: Return latest multi-camera ANPR capability assessment results.
    """
    if anpr_assessor.latest_assessment:
        return anpr_assessor.latest_assessment
    
    return {"status":"NOT_RUN", "results":[]}

@router.get("/anpr-assessment/{camera_id}")
async def get_camera_anpr_assessment(camera_id: str):
    """
    Return detailed ANPR suitability metrics for a specific camera.
    """
    assessment = anpr_assessor.latest_assessment
    if not assessment:
        assessment = {"results": []}
    
    results = assessment.get("results", [])
    cam_res = next((r for r in results if r["camera_id"] == camera_id), None)
    if not cam_res:
        raise HTTPException(status_code=404, detail=f"No assessment record found for camera '{camera_id}'.")
    return cam_res

@router.post("/anpr-assessment/run")
async def run_fresh_anpr_assessment(
    duration: int = Query(default=15, ge=5, le=60, description="Duration in seconds per camera"),
    camera_id: Optional[str] = Query(default=None, description="Optional specific camera ID to assess")
):
    """
    Trigger a fresh sequential multi-camera ANPR capability assessment job.
    """
    if anpr_assessor.is_running:
        return {
            "status": "RUNNING",
            "message": "ANPR assessment job is already running in background.",
            "latest_assessment": anpr_assessor.latest_assessment
        }

    summary = await anpr_assessor.run_assessment_all_cameras(
        duration_per_camera=duration,
        target_camera_id=camera_id
    )
    return {
        "status": "COMPLETED",
        "assessment_id": summary["assessment_id"],
        "total_cameras": summary["total_cameras"],
        "recommended_cameras": summary["recommended_cameras"],
        "summary": summary
    }

# =====================================================================
# PHASE 1 CAMERA CATALOGUE APIs
# =====================================================================

@router.get("", response_model=List[Dict[str, Any]])
async def list_cameras(refresh: bool = False):
    """
    PHASE 1: Fetch and return official camera catalogue dynamically.
    Automatically starts priority streams (cam04, cam06, cam15) if no workers are active.
    """
    try:
        cameras = await catalogue_service.fetch_catalogue(force_refresh=refresh)
        
        active_statuses = stream_manager.get_all_statuses()
        for cam in cameras:
            cam_id = cam["id"]
            if cam_id in active_statuses:
                cam["stream_telemetry"] = active_statuses[cam_id]
                cam["connection_status"] = active_statuses[cam_id]["status"]
            else:
                cam["stream_telemetry"] = None
                cam["connection_status"] = "DISCONNECTED"

        return [public_camera(c) for c in cameras]
    except Exception as e:
        logger.error(f"Error fetching cameras catalogue: {e}")
        raise HTTPException(status_code=503, detail=f"Camera catalogue temporarily unavailable: {str(e)}")

@router.get("/{camera_id}")
async def get_camera(camera_id: str):
    """Get metadata for a specific camera."""
    cam = await catalogue_service.get_camera_by_id(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found in catalogue.")
    
    worker = stream_manager.get_worker(camera_id)
    status_info = worker.get_status() if worker else None
    cam["stream_telemetry"] = status_info
    cam["connection_status"] = status_info["status"] if status_info else "OFFLINE"
    return public_camera(cam)

@router.post("/{camera_id}/connect")
async def connect_camera(camera_id: str,request: Request):
    require_role(request,"operator")
    """Start streaming worker for specified camera."""
    cam = await catalogue_service.get_camera_by_id(camera_id)
    if not cam:
        raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found.")
    
    rtsp_url = cam["rtsp_url"]
    if not rtsp_url:
        raise HTTPException(422,"Configure a video source in the registry first")
    worker = stream_manager.start_camera(camera_id, rtsp_url)
    sighting_repo.set_connection_intent(camera_id,True,actor(request)['name'])
    return {
        "status": "SUCCESS",
        "message": f"Stream worker started for camera '{camera_id}'",
        "camera": public_camera(cam),
        "stream_telemetry": worker.get_status()
    }

@router.post("/{camera_id}/disconnect")
async def disconnect_camera(camera_id: str,request: Request):
    require_role(request,"operator")
    """Stop streaming worker for specified camera."""
    stopped = stream_manager.stop_camera(camera_id)
    if not stopped:
        raise HTTPException(status_code=404, detail=f"Camera '{camera_id}' was not actively streaming.")
    sighting_repo.set_connection_intent(camera_id,False,actor(request)['name'])
    return {"status": "SUCCESS", "message": f"Stream worker stopped for camera '{camera_id}'"}

@router.get("/{camera_id}/health")
async def get_camera_health(camera_id: str):
    """
    PHASE 12 TASK 12 API: Return camera health telemetry for GPU, RTSP, FPS, and streaming status.
    """
    worker = stream_manager.get_worker(camera_id)
    if not worker:
        cam = await catalogue_service.get_camera_by_id(camera_id)
        if not cam:
            raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found in catalogue.")
        from app.services.yolo_service import yolo_detector
        return {
            "camera_id": camera_id,
            "connection": "OFFLINE",
            "streaming": False,
            "frames_received": 0,
            "fps": 0.0,
            "resolution": "N/A",
            "last_frame_age_ms": None,
            "gpu": yolo_detector.device_name,
            "cuda": yolo_detector.cuda_available,
            "error": "Stream worker not started"
        }
    return worker.get_health()

@router.get("/{camera_id}/stream-status")
async def get_camera_stream_status(camera_id: str):
    """
    PHASE 10.1 API: Return stream health & worker status for a specific camera.
    """
    worker = stream_manager.get_worker(camera_id)
    if not worker:
        cam = await catalogue_service.get_camera_by_id(camera_id)
        if not cam:
            raise HTTPException(status_code=404, detail=f"Camera ID '{camera_id}' not found.")
        return {
            "camera_id": camera_id,
            "rtsp_status": "OFFLINE",
            "worker_running": False,
            "frames_received": 0,
            "latest_frame_available": False,
            "yolo_processing": False,
            "stream_clients": 0,
            "last_frame_timestamp": None,
            "error_message": "Stream worker not started"
        }
    return worker.get_status()
