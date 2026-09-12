"""
Investigation, Registry, Watchlist & Alerts API.

These endpoints expose the durable sighting spine (see sighting_repository.py) to the
frontend. They implement the graded hackathon test case: given a plate, return its
timestamped route across cameras, with watchlist cross-referencing and automated alerts.

All routes are thin wrappers over the synchronous SightingRepository. Query load is
light (operator dashboard), so calling the sync repo directly from async handlers is
acceptable at hackathon scale. See CONTRACT.md §3 and §4 for the frozen shapes.
"""
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from app.security import actor, require_role
from app.api.registry_tools import public_camera, CSVImport, parse_rows
from app.services.sighting_repository import sighting_repo

logger = logging.getLogger(__name__)

registry_router = APIRouter(prefix="/api/registry", tags=["Camera Registry & GIS"])
investigation_router = APIRouter(prefix="/api/investigation", tags=["Vehicle Investigation & Trace"])
watchlist_router = APIRouter(prefix="/api/watchlist", tags=["Watchlist"])
alerts_router = APIRouter(prefix="/api/alerts", tags=["Alerts"])


# ---------- Registry & GIS ----------
@registry_router.get("/cameras", response_model=List[Dict[str, Any]])
async def registry_cameras():
    """All cameras with geo + department + ANPR capability. The GIS map reads this."""
    from app.services.stream_manager import stream_manager
    states = stream_manager.get_all_statuses()
    return [dict(public_camera(c),connection_status=states.get(c['id'],{}).get('status','DISCONNECTED')) for c in sighting_repo.list_cameras()]


@registry_router.get("/stats")
async def registry_stats():
    return sighting_repo.stats()


# ---------- Investigation / Trace ----------
@investigation_router.get("/trace/{plate_number}")
async def trace_vehicle(plate_number: str, request: Request, from_time: Optional[str]=None, to_time: Optional[str]=None, source_type: Optional[str]=None):
    """THE graded test case. Returns the full timestamped, location-wise route for a plate."""
    sighting_repo.audit(actor(request)["name"],"VEHICLE_SEARCH",plate_number)
    try:
        return sighting_repo.trace_plate(plate_number,from_time,to_time,source_type)
    except ValueError as e:
        raise HTTPException(422,str(e))


@investigation_router.get("/sightings", response_model=List[Dict[str, Any]])
async def list_sightings(
    plate: Optional[str] = None,
    camera_id: Optional[str] = None,
    limit: int = Query(200, ge=1, le=1000),
):
    return sighting_repo.list_sightings(plate=plate, camera_id=camera_id, limit=limit)


# ---------- Watchlist ----------
class WatchlistCreate(BaseModel):
    plate_number: str = Field(min_length=1,max_length=30)
    reason: Literal["STOLEN","WANTED","SUSPECT","MISSING","BOLO"] = "BOLO"
    severity: Literal["HIGH","MEDIUM","LOW"] = "MEDIUM"
    description: Optional[str] = None
    source: str = Field(default="MANUAL",max_length=100)

    @field_validator("plate_number")
    @classmethod
    def valid_plate(cls,value):
        from app.services.sighting_repository import normalize_plate
        value = normalize_plate(value)
        if not value: raise ValueError("Plate must contain letters or digits")
        return value


@watchlist_router.get("", response_model=List[Dict[str, Any]])
async def get_watchlist(active_only: bool = True):
    return sighting_repo.list_watchlist(active_only=active_only)


@watchlist_router.post("")
async def create_watchlist(entry: WatchlistCreate, request: Request):
    require_role(request,"admin")
    sighting_repo.audit(actor(request)["name"],"WATCHLIST_UPSERT",entry.plate_number)
    try:
        return sighting_repo.add_watchlist(**entry.model_dump())
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@watchlist_router.delete("/{wl_id}")
async def remove_watchlist(wl_id: int,request: Request):
    require_role(request,"admin")
    if not any(w["id"] == wl_id for w in sighting_repo.list_watchlist(False)):
        raise HTTPException(404,"Watchlist entry not found")
    sighting_repo.audit(actor(request)["name"],"WATCHLIST_REMOVE",wl_id)
    sighting_repo.delete_watchlist(wl_id)
    return {"deleted": wl_id}


# ---------- Alerts ----------
@alerts_router.get("", response_model=List[Dict[str, Any]])
async def get_alerts(
    acknowledged: Optional[bool] = None,
    limit: int = Query(100, ge=1, le=500),
):
    return sighting_repo.list_alerts(acknowledged=acknowledged, limit=limit)


@alerts_router.post("/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int,request: Request):
    require_role(request,"operator")
    with sighting_repo._lock:
        if not sighting_repo._connect().execute("SELECT id FROM alerts WHERE id=?",(alert_id,)).fetchone():
            raise HTTPException(404,"Alert not found")
    sighting_repo.audit(actor(request)["name"],"ALERT_ACKNOWLEDGE",alert_id)
    sighting_repo.acknowledge_alert(alert_id)
    return {"acknowledged": alert_id}


@watchlist_router.post('/import')
def import_watchlist(body: CSVImport, request: Request):
    require_role(request,'admin')
    rows = parse_rows(body.csv,WatchlistCreate)
    for row in rows:
        sighting_repo.add_watchlist(**row)
    sighting_repo.audit(actor(request)['name'],'WATCHLIST_IMPORT',len(rows))
    return {'imported':len(rows)}
