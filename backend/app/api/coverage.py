"""Survey-based geographic gaps, with no invented footprints or coordinates."""
import json
import math
from datetime import datetime, timezone
from typing import Literal, Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field
from shapely.geometry import shape, mapping
from shapely.ops import transform, unary_union
from pyproj import Transformer
from app.security import actor, require_role
from app.services.sighting_repository import sighting_repo

router=APIRouter(prefix='/api/registry/coverage',tags=['Surveyed geographic coverage'])
TO_METRES=Transformer.from_crs(4326,6933,always_xy=True).transform
TO_COORDS=Transformer.from_crs(6933,4326,always_xy=True).transform

class Properties(BaseModel):
    id: str=Field(pattern=r'^[A-Za-z0-9_-]{1,64}$')
    name: str=Field(min_length=1,max_length=160)
    kind: Literal['AREA','CAMERA']
    provenance: Literal['VERIFIED','REPRESENTATIVE']
    camera_id: Optional[str]=None

class Feature(BaseModel):
    type: Literal['Feature']='Feature'
    properties: Properties
    geometry: dict

class Survey(BaseModel):
    type: Literal['FeatureCollection']='FeatureCollection'
    features: list[Feature]=Field(min_length=1,max_length=500)

def validate_feature(feature):
    value=feature.model_dump()
    if len(json.dumps(value))>200000: raise HTTPException(422,'A survey feature exceeds the geometry size limit')
    try:
        geometry=shape(value['geometry'])
        if geometry.geom_type not in ('Polygon','MultiPolygon') or geometry.is_empty or not geometry.is_valid or geometry.has_z:
            raise ValueError()
        west,south,east,north=geometry.bounds
        if not all(math.isfinite(v) for v in geometry.bounds) or not (-180<=west<east<=180 and -85<=south<north<=85) or east-west>180:
            raise ValueError()
    except Exception:
        raise HTTPException(422,'Use valid nonempty 2D Polygon/MultiPolygon geometry in longitude/latitude')
    props=value['properties']
    if props['kind']=='CAMERA' and not sighting_repo.get_camera(props['camera_id']):
        raise HTTPException(422,'Coverage footprints must reference an onboarded camera')
    return value

def audit_in(conn,request,action,target):
    conn.execute('INSERT INTO audit_log(actor,action,target,created_at) VALUES(?,?,?,?)',
                 (actor(request)['name'],action,target,datetime.now(timezone.utc).isoformat()))

@router.post('')
def import_surveys(body: Survey,request: Request):
    require_role(request,'admin')
    values=[validate_feature(feature) for feature in body.features]
    if len(json.dumps(values))>2_000_000: raise HTTPException(422,'Survey import exceeds 2 MB')
    ids=[value['properties']['id'] for value in values]
    if len(ids)!=len(set(ids)): raise HTTPException(422,'Duplicate survey IDs')
    with sighting_repo._lock,sighting_repo._connect() as conn:
        for value in values:
            conn.execute('INSERT INTO coverage_layers(id,feature_json) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET feature_json=excluded.feature_json',
                         (value['properties']['id'],json.dumps(value)))
        audit_in(conn,request,'COVERAGE_IMPORT',','.join(ids))
    return {'imported':len(values)}

@router.get('')
def list_surveys():
    with sighting_repo._lock:
        features=[json.loads(row[0]) for row in sighting_repo._connect().execute('SELECT feature_json FROM coverage_layers ORDER BY id')]
    return {'type':'FeatureCollection','features':features}

@router.get('/gaps')
def coverage_gaps():
    features=list_surveys()['features']
    verified=[f for f in features if f['properties']['provenance']=='VERIFIED']
    footprints=[transform(TO_METRES,shape(f['geometry'])) for f in verified if f['properties']['kind']=='CAMERA']
    coverage=unary_union(footprints)
    reports=[]
    for feature in verified:
        if feature['properties']['kind']!='AREA': continue
        area=transform(TO_METRES,shape(feature['geometry']))
        covered=area.intersection(coverage)
        gap=area.difference(coverage)
        reports.append(dict(area_id=feature['properties']['id'],name=feature['properties']['name'],
                            area_m2=round(area.area,2),covered_m2=round(covered.area,2),uncovered_m2=round(gap.area,2),
                            coverage_percent=round(100*covered.area/area.area,2),
                            uncovered_geometry=None if gap.is_empty else mapping(transform(TO_COORDS,gap))))
    return {'status':'MEASURED' if reports else 'MISSING_VERIFIED_AREA','areas':reports,
            'verified_camera_footprints':len(footprints),
            'scope':'Geometric coverage of supplied verified survey footprints, using EPSG:6933 equal-area measurements. This does not establish operational availability, plate readability, occlusion-free visibility or coverage beyond the survey.',
            'excluded_representative_features':len(features)-len(verified)}

@router.delete('/{survey_id}')
def remove_survey(survey_id: str,request: Request):
    require_role(request,'admin')
    with sighting_repo._lock,sighting_repo._connect() as conn:
        result=conn.execute('DELETE FROM coverage_layers WHERE id=?',(survey_id,))
        if not result.rowcount: raise HTTPException(404,'Survey feature not found')
        audit_in(conn,request,'COVERAGE_DELETE',survey_id)
    return {'deleted':survey_id}
