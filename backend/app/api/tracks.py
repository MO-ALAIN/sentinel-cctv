import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.track_manager import track_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/tracks", tags=["Vehicle Tracks"])

@router.get("", response_model=List[Dict[str, Any]])
async def get_all_tracks(
    camera_id: Optional[str] = None,
    status: Optional[str] = Query(default=None, description="Filter by status: ACTIVE or INACTIVE"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    PHASE 6 Output API: Return active and recent persistent vehicle tracks.
    """
    return track_manager.get_tracks(camera_id=camera_id, status_filter=status, limit=limit)

@router.get("/summary")
async def get_track_summary():
    """
    Return summary tracking statistics (total unique tracks, active tracks).
    """
    return track_manager.get_summary_stats()

@router.get("/{camera_id}", response_model=List[Dict[str, Any]])
async def get_camera_tracks(
    camera_id: str,
    status: Optional[str] = Query(default=None, description="Filter by status: ACTIVE or INACTIVE")
):
    """
    Get vehicle tracks specific to a single camera.
    """
    return track_manager.get_tracks(camera_id=camera_id, status_filter=status)
