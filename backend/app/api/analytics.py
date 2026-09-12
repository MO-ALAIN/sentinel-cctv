import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.traffic_analytics import traffic_analytics_engine
from app.services.incident_detector import incident_engine

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/analytics", tags=["Traffic Analytics"])
events_router = APIRouter(prefix="/api/events", tags=["Traffic Events"])

@router.get("/summary")
async def get_system_summary():
    """
    PHASE 8 API: Return multi-camera system traffic summary.
    """
    return traffic_analytics_engine.get_system_summary()

@router.get("", response_model=List[Dict[str, Any]])
async def get_all_analytics():
    """
    PHASE 8 API: Return analytics breakdown for all active cameras.
    """
    return traffic_analytics_engine.get_all_analytics()

@router.get("/{camera_id}")
async def get_camera_analytics(camera_id: str):
    """
    PHASE 8 API: Return real-time traffic & vehicle analytics for a specific camera.
    """
    if camera_id not in traffic_analytics_engine.cameras:
        cam_obj = traffic_analytics_engine.get_camera_analytics(camera_id)
        return cam_obj.get_analytics()
    
    return traffic_analytics_engine.cameras[camera_id].get_analytics()

@events_router.get("/summary")
async def get_events_summary():
    """
    PHASE 9 API: Return aggregated summary of events across cameras (active, by type, by camera).
    """
    return incident_engine.get_events_summary()

@events_router.get("", response_model=List[Dict[str, Any]])
async def get_traffic_events(
    camera_id: Optional[str] = Query(default=None, description="Filter events by camera ID"),
    event_type: Optional[str] = Query(default=None, description="Filter events by type"),
    status: Optional[str] = Query(default=None, description="Filter events by status (ACTIVE, RESOLVED, EXPIRED)"),
    severity: Optional[str] = Query(default=None, description="Filter events by severity (LOW, MEDIUM, HIGH)")
):
    """
    PHASE 9 API: Return traffic events log with optional filtering.
    """
    all_evts = incident_engine.events_db
    filtered = []
    for e in all_evts:
        if camera_id and e.get("camera_id") != camera_id:
            continue
        if event_type and e.get("event_type") != event_type:
            continue
        if status and e.get("status") != status:
            continue
        if severity and e.get("severity") != severity:
            continue
        filtered.append(e)

    filtered.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
    return filtered

@events_router.get("/{event_id}")
async def get_event_by_id(event_id: str):
    """
    PHASE 9 API: Return detailed event information for a single event ID.
    """
    evt = next((e for e in incident_engine.events_db if e.get("event_id") == event_id), None)
    if not evt:
        raise HTTPException(status_code=404, detail=f"Event ID '{event_id}' not found.")
    return evt
