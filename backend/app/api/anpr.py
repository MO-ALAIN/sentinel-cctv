import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from app.services.anpr_service import anpr_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/anpr", tags=["ANPR License Plate Recognition"])

@router.get("", response_model=List[Dict[str, Any]])
async def get_anpr_records(
    camera_id: Optional[str] = None,
    track_id: Optional[int] = None,
    plate_number: Optional[str] = None,
    status: Optional[str] = Query(default=None, description="Filter by status: CONFIRMED, LOW_CONFIDENCE, UNREADABLE"),
    limit: int = Query(default=100, ge=1, le=500)
):
    """
    PHASE 7 API: Return recent ANPR license plate recognition records.
    """
    return anpr_manager.get_records(
        camera_id=camera_id,
        track_id=track_id,
        plate_number=plate_number,
        status=status,
        limit=limit
    )

@router.get("/search/{plate_number}", response_model=List[Dict[str, Any]])
async def search_plate_records(plate_number: str):
    """
    Search ANPR records by full or partial license plate registration number.
    """
    return anpr_manager.search_plate(query=plate_number)

@router.get("/stats")
async def get_anpr_telemetry():
    """
    Expose ANPR performance telemetry (OCR engine, GPU status, detection/OCR latency, accuracy stats).
    """
    return anpr_manager.get_telemetry()
