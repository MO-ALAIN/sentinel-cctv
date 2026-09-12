"""Validated onboarding, reporting and evidence endpoints for the registry foundation."""
import csv
import io
from datetime import datetime
from typing import Literal, Optional
from urllib.parse import urlsplit, urlunsplit
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import Response, FileResponse
from pydantic import BaseModel, Field, ValidationError, model_validator, field_validator
from app.paths import MEDIA_DIR, EVIDENCE_DIR, contained_file
from app.services.sighting_repository import sighting_repo, normalize_plate, canonical_time
from app.security import actor, require_role

router = APIRouter(tags=['Registry onboarding and reports'])

def public_camera(cam):
    result = dict(cam)
    value = result.get('rtsp_url') or ''
    parsed = urlsplit(value)
    if parsed.scheme:
        host = parsed.hostname or ''
        if ':' in host:
            host = f'[{host}]'
        result['rtsp_url'] = urlunsplit((parsed.scheme,host+(f':{parsed.port}' if parsed.port else ''),parsed.path,'',''))
    else:
        result['rtsp_url'] = ''
    return result

class CameraCreate(BaseModel):
    id: str = Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    name: str = Field(min_length=1,max_length=160)
    location: str = Field(default='',max_length=200)
    district: str = Field(default='',max_length=100)
    department: str = Field(default='',max_length=100)
    lat: Optional[float] = Field(default=None,ge=-90,le=90,allow_inf_nan=False)
    lon: Optional[float] = Field(default=None,ge=-180,le=180,allow_inf_nan=False)
    rtsp_url: str = Field(default='',max_length=2048)
    source_type: Literal['LIVE','GOVERNMENT_REPLAY','RECORDED'] = 'LIVE'
    source_system: str = Field(default='',max_length=120)
    camera_type: Literal['IP','ANALOG_DVR','VMS','FILE'] = 'IP'
    ownership: str = Field(default='',max_length=160)
    storage_details: str = Field(default='',max_length=300)
    retention_days: Optional[int] = Field(default=None,ge=0,le=3650)
    maintenance_status: Literal['UNKNOWN','CURRENT','DUE','FAULT'] = 'UNKNOWN'
    geo_source: Literal['UNKNOWN','VERIFIED','REPRESENTATIVE'] = 'UNKNOWN'
    recording_started_at: Optional[str] = None
    stream_codec: Optional[str] = Field(default='',max_length=40)
    stream_width: Optional[int] = Field(default=None,ge=1,le=32768)
    stream_height: Optional[int] = Field(default=None,ge=1,le=32768)
    declared_fps: Optional[float] = Field(default=None,ge=0,le=1000,allow_inf_nan=False)
    catalogue_live: Optional[bool] = None

    @model_validator(mode='after')
    def validate_source(self):
        if (self.lat is None) != (self.lon is None):
            raise ValueError('Provide both latitude and longitude')
        if self.lat is not None and self.geo_source == 'UNKNOWN':
            raise ValueError('Identify coordinates as verified or representative')
        if self.recording_started_at:
            self.recording_started_at = canonical_time(self.recording_started_at)
        if self.rtsp_url:
            if self.source_type == 'RECORDED':
                if not contained_file(MEDIA_DIR,self.rtsp_url).is_file():
                    raise ValueError('Recording must exist inside CCTV_MEDIA_DIR')
            else:
                parsed = urlsplit(self.rtsp_url)
                if parsed.scheme not in ('rtsp','rtsps','http','https') or not parsed.hostname:
                    raise ValueError('Use an RTSP or HTTP(S) source URL with a host')
                _ = parsed.port  # Reject malformed ports before storage/redaction.
        return self

class CSVImport(BaseModel):
    csv: str = Field(min_length=1,max_length=2_000_000)

def parse_rows(text, model):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    rows, errors = [], []
    for index, row in enumerate(reader,2):
        if index > 5001:
            raise HTTPException(400,'Maximum 5,000 rows per import')
        try:
            if None in row:
                raise ValueError('Too many columns in CSV row')
            cleaned = {k:v.strip() for k,v in row.items() if k and v is not None and v.strip()}
            rows.append(model.model_validate(cleaned).model_dump())
        except (ValidationError,ValueError) as e:
            errors.append({'row':index,'error':str(e)})
    if errors or not rows:
        raise HTTPException(422, {'errors':errors or [{'row':1,'error':'No data rows'}]})
    return rows

def csv_response(rows, filename, fields=None):
    output = io.StringIO(newline='')
    fields = fields or (list(rows[0]) if rows else ['id'])
    writer = csv.DictWriter(output,fieldnames=fields,extrasaction='ignore')
    writer.writeheader()
    for row in rows:
        safe = {k: ("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()}
        writer.writerow(safe)
    return Response(output.getvalue(),media_type='text/csv',headers={'Content-Disposition':f'attachment; filename="{filename}"'})

def prepare_camera(values):
    previous = sighting_repo.get_camera(values['id'])
    if not values['rtsp_url'] and previous:
        values['rtsp_url'] = previous.get('rtsp_url') or ''
    try:
        return CameraCreate.model_validate(values).model_dump()
    except ValueError:
        raise HTTPException(422,'Source settings are invalid; supply a compatible URL when changing source type')


def stop_edited_feeds(rows):
    from app.services.stream_manager import stream_manager
    for row in rows:
        if stream_manager.get_worker(row['id']):
            stream_manager.stop_camera(row['id'])
        sighting_repo.set_connection_intent(row['id'],False,'registry edit')


@router.post('/api/registry/cameras')
def onboard(body: CameraCreate,request: Request):
    require_role(request,'admin')
    values = prepare_camera(body.model_dump())
    stop_edited_feeds([values])
    sighting_repo.save_cameras([values],actor(request)["name"])
    return public_camera(sighting_repo.get_camera(body.id))

@router.post('/api/registry/import')
def import_cameras(body: CSVImport,request: Request):
    require_role(request,'admin')
    rows = parse_rows(body.csv,CameraCreate)
    ids = [r['id'] for r in rows]
    if len(ids) != len(set(ids)):
        raise HTTPException(422,'Duplicate camera IDs in import')
    rows = [prepare_camera(row) for row in rows]
    stop_edited_feeds(rows)
    sighting_repo.save_cameras(rows,actor(request)['name'])
    return {'imported':len(rows)}

@router.get('/api/registry/export')
def export_cameras(request: Request):
    sighting_repo.audit(actor(request)['name'],'CAMERA_EXPORT','registry')
    return csv_response([public_camera(c) for c in sighting_repo.list_cameras()],'camera-registry.csv')

@router.get('/api/registry/gaps')
def gaps():
    from app.services.stream_manager import stream_manager
    states = stream_manager.get_all_statuses()
    findings = []
    for cam in sighting_repo.list_cameras():
        issues = []
        if cam['lat'] is None or cam['lon'] is None: issues.append('MISSING_COORDINATES')
        elif cam['geo_source'] != 'VERIFIED': issues.append('UNVERIFIED_COORDINATES')
        if not cam['department']: issues.append('MISSING_DEPARTMENT')
        if not cam['source_system']: issues.append('MISSING_SOURCE_SYSTEM')
        if not cam['storage_details']: issues.append('MISSING_RETENTION_DETAILS')
        if cam['maintenance_status'] in ('DUE','FAULT','UNKNOWN'): issues.append('MAINTENANCE_'+cam['maintenance_status'])
        if states.get(cam['id'],{}).get('status') != 'CONNECTED': issues.append('NO_ACTIVE_FEED')
        if issues: findings.append({'camera_id':cam['id'],'name':cam['name'],'issues':issues})
    return {'generated_at':datetime.now().astimezone().isoformat(), 'findings':findings,
            'scope':'Metadata and operational gaps. Geographic blind spots require surveyed coverage polygons and area boundaries.'}

@router.get('/api/registry/audit')
def audits(request: Request):
    require_role(request,'admin')
    return sighting_repo.audit_history()

@router.get('/api/investigation/export')
def export_sightings(request: Request,plate: Optional[str]=None,camera_id: Optional[str]=None,
                     from_time: Optional[str]=None,to_time: Optional[str]=None,source_type: Optional[str]=None):
    try:
        rows = sighting_repo.trace_plate(plate,from_time,to_time,source_type)['route'] if plate else sighting_repo.list_sightings(camera_id=camera_id,limit=100000)
        if from_time: rows = [r for r in rows if r['sighted_at'] >= canonical_time(from_time)]
        if to_time: rows = [r for r in rows if r['sighted_at'] <= canonical_time(to_time)]
    except ValueError as e:
        raise HTTPException(422,str(e))
    if source_type: rows = [r for r in rows if r['source_type'] == source_type]
    if camera_id: rows = [r for r in rows if r['camera_id'] == camera_id]
    for row in rows: row.pop('crop_path',None)
    sighting_repo.audit(actor(request)['name'],'SIGHTING_EXPORT',normalize_plate(plate) or 'filtered observations')
    return csv_response(rows,'vehicle-observations.csv',fields=['id','plate_number','camera_id','sighted_at','location','lat','lon','geo_source','vehicle_type','status','confidence','source_type','session_id','media_offset_seconds','timestamp_basis'])

@router.get('/api/investigation/evidence/{sighting_id}')
def evidence(sighting_id: int,request: Request):
    row = sighting_repo.get_sighting(sighting_id)
    if not row or not row['crop_path']: raise HTTPException(404,'No saved evidence for this observation')
    try: path = contained_file(EVIDENCE_DIR,row['crop_path'])
    except ValueError: raise HTTPException(404,'Evidence unavailable')
    if not path.is_file(): raise HTTPException(404,'Evidence file unavailable')
    sighting_repo.audit(actor(request)['name'],'EVIDENCE_VIEW',sighting_id)
    return FileResponse(path,media_type='image/jpeg')
