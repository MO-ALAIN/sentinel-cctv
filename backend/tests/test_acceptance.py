"""Requirement-level checks with isolated synthetic records, never production sightings."""
import os
os.environ['AI_ENABLED'] = 'false'
import csv
import io
import threading
import time
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app.api import investigation, registry_tools, coverage, detections
from app.security import access_middleware, router as auth_router, SESSIONS
from app.services.sighting_repository import sighting_repo, SightingRepository

@pytest.fixture
def client(tmp_path,monkeypatch):
    sighting_repo.close()
    monkeypatch.setattr(sighting_repo,'_db_filename',str(tmp_path/'test.db'))
    monkeypatch.delenv('CCTV_ADMIN_PASSWORD',raising=False)
    app=FastAPI()
    app.middleware('http')(access_middleware)
    for router in (auth_router,registry_tools.router,coverage.router,detections.router,investigation.registry_router,
                   investigation.investigation_router,investigation.watchlist_router,investigation.alerts_router):
        app.include_router(router)
    with TestClient(app) as c:
        yield c
    sighting_repo.close()
    SESSIONS.clear()

def camera(cid,**kwargs):
    return dict(id=cid,name='Test camera '+cid,location='Synthetic test location',lat=22.3,lon=73.1,
                geo_source='REPRESENTATIVE',department='TEST',source_system='TEST',**kwargs)

def test_onboarding_and_atomic_csv_validation(client):
    assert client.post('/api/registry/cameras',json=camera('A')).status_code==200
    before=sighting_repo.stats()['cameras_registered']
    bad='id,name,lat,lon,geo_source\nB,Valid,22,73,VERIFIED\nC,Invalid,999,73,VERIFIED\n'
    assert client.post('/api/registry/import',json={'csv':bad}).status_code==422
    assert sighting_repo.stats()['cameras_registered']==before
    good='id,name,department,source_system\nB,Camera B,TEST,System B\n'
    assert client.post('/api/registry/import',json={'csv':good}).json()['imported']==1
    assert len(client.get('/api/registry/cameras').json())==2

def test_vehicle_history_watchlist_alert_and_restart(client):
    for cid in ('A','B'): assert client.post('/api/registry/cameras',json=camera(cid)).status_code==200
    assert client.post('/api/watchlist',json={'plate_number':'gj-01 ab 1234','reason':'STOLEN','severity':'HIGH'}).status_code==200
    sighting_repo.record_sighting(plate_number='GJ01AB1234',camera_id='B',track_id=1,session_id='b',status='CONFIRMED',sighted_at='2026-09-05T10:05:00Z')
    sighting_repo.record_sighting(plate_number='GJ01AB1234',camera_id='A',track_id=1,session_id='a',status='CONFIRMED',sighted_at='2026-09-05T15:30:00+05:30')
    sighting_repo.close()
    trace=client.get('/api/investigation/trace/gj-01ab1234').json()
    assert [r['camera_id'] for r in trace['route']]==['A','B']
    assert trace['distinct_cameras']==2 and trace['on_watchlist']
    alerts=client.get('/api/alerts?acknowledged=false').json()
    assert len(alerts)==2
    assert client.post(f"/api/alerts/{alerts[0]['id']}/acknowledge").status_code==200
    assert len(client.get('/api/alerts?acknowledged=false').json())==1
    exported=client.get('/api/investigation/export?plate=GJ01AB1234')
    assert exported.status_code==200
    rows=list(csv.DictReader(io.StringIO(exported.text)))
    assert len(rows)==2 and rows[0]['sighted_at'].endswith('+00:00')

def test_uncertain_observations_do_not_trigger_confirmed_alert(client):
    client.post('/api/registry/cameras',json=camera('A'))
    client.post('/api/watchlist',json={'plate_number':'TEST123'})
    sighting_repo.record_sighting(plate_number='TEST123',camera_id='A',status='LOW_CONFIDENCE',confidence=.3)
    assert client.get('/api/alerts').json()==[]
    assert client.get('/api/investigation/trace/TEST123').json()['total_sightings']==1

def test_session_deduplication_and_new_appearance(client):
    client.post('/api/registry/cameras',json=camera('A'))
    record=dict(plate_number='TEST123',camera_id='A',track_id=7,status='CONFIRMED')
    sighting_repo.record_sighting(**record,session_id='one')
    sighting_repo.record_sighting(**record,session_id='one')
    sighting_repo.record_sighting(**record,session_id='two')
    assert sighting_repo.trace_plate('TEST123')['total_sightings']==2

def test_sighting_and_alert_rollback_together(client,monkeypatch):
    client.post('/api/registry/cameras',json=camera('A'))
    def fail(*args): raise RuntimeError('Simulated transaction interruption')
    monkeypatch.setattr(sighting_repo,'_match_and_alert',fail)
    with pytest.raises(RuntimeError):
        sighting_repo.record_sighting(plate_number='TEST123',camera_id='A',status='CONFIRMED')
    assert sighting_repo.stats()['total_sightings']==0

def test_filters_and_no_match(client):
    client.post('/api/registry/cameras',json=camera('A',source_type='GOVERNMENT_REPLAY'))
    sighting_repo.record_sighting(plate_number='TEST123',camera_id='A',status='CONFIRMED',sighted_at='2026-09-05T10:00:00Z')
    assert client.get('/api/investigation/trace/TEST123?source_type=LIVE').json()['total_sightings']==0
    assert client.get('/api/investigation/trace/TEST123?from_time=2026-09-06T00:00:00Z').json()['total_sightings']==0
    assert client.get('/api/investigation/trace/NOMATCH').json()['route']==[]
    assert client.get('/api/investigation/trace/TEST123?from_time=invalid').status_code==422

def test_evidence_containment_and_secret_redaction(client,tmp_path,monkeypatch):
    client.post('/api/registry/cameras',json=camera('A',rtsp_url='rtsp://example:password@camera.test:8554/stream?token=secret'))
    public=client.get('/api/registry/cameras').text
    assert 'password' not in public and 'secret' not in public
    r=sighting_repo.record_sighting(plate_number='TEST123',camera_id='A',status='CONFIRMED',crop_path='../outside.jpg')
    assert client.get(f"/api/investigation/evidence/{r['sighting_id']}").status_code==404
    monkeypatch.setattr(registry_tools,'EVIDENCE_DIR',tmp_path)
    (tmp_path/'inside.jpg').write_bytes(b'test-image-content')
    r=sighting_repo.record_sighting(plate_number='TEST123',camera_id='A',status='CONFIRMED',crop_path='inside.jpg')
    assert client.get(f"/api/investigation/evidence/{r['sighting_id']}").content==b'test-image-content'

def test_camera_edit_keeps_private_source(client):
    client.post('/api/registry/cameras',json=camera('A',rtsp_url='rtsp://example:password@camera.test/source'))
    client.post('/api/registry/cameras',json=camera('A',rtsp_url=''))
    assert 'password' in sighting_repo.get_camera('A')['rtsp_url']

def test_access_roles_and_cross_origin(client,monkeypatch):
    monkeypatch.setenv('CCTV_ADMIN_PASSWORD','test-admin-only')
    monkeypatch.setenv('CCTV_VIEWER_PASSWORD','test-viewer-only')
    assert client.get('/api/registry/cameras').status_code==401
    assert client.post('/api/auth/login',json={'username':'viewer','password':'test-viewer-only'}).status_code==200
    assert client.get('/api/registry/cameras').status_code==200
    assert client.post('/api/registry/cameras',json=camera('A')).status_code==403
    assert client.post('/api/auth/logout').status_code==200
    assert client.post('/api/auth/login',json={'username':'admin','password':'test-admin-only'}).status_code==200
    assert client.post('/api/registry/cameras',json=camera('A'),headers={'Origin':'https://untrusted.example'}).status_code==403
    assert client.post('/api/registry/cameras',json=camera('A')).status_code==200

def test_gaps_and_audits(client):
    client.post('/api/registry/cameras',json=camera('A'))
    report=client.get('/api/registry/gaps').json()
    assert 'UNVERIFIED_COORDINATES' in report['findings'][0]['issues']
    assert client.get('/api/registry/audit').json()[0]['action']=='CAMERA_UPSERT'

def test_empty_frame_access_never_deadlocks():
    from app.services.stream_worker import RTSPStreamWorker
    from app.services.demo_stream_worker import DemoStreamWorker
    workers=[RTSPStreamWorker('T',''),DemoStreamWorker('T','','','','','')]
    for worker in workers:
        thread=threading.Thread(target=worker.get_latest_annotated_frame,daemon=True)
        thread.start();thread.join(timeout=.5)
        assert not thread.is_alive()

def test_missing_watchlist_and_alert_return_404(client):
    assert client.delete('/api/watchlist/99999').status_code==404
    assert client.post('/api/alerts/99999/acknowledge').status_code==404

def test_anpr_requires_independent_frames_and_retries_failed_write(client,monkeypatch):
    import numpy as np
    from app.services.anpr_service import ANPRManager, modular_plate_detector
    client.post('/api/registry/cameras',json=camera('A'))
    client.post('/api/watchlist',json={'plate_number':'GJ01AB1234'})
    crop=np.random.default_rng(1).integers(0,255,(60,240,3),dtype=np.uint8)
    monkeypatch.setattr(modular_plate_detector,'detect_plates',lambda *a,**kw:[{
        'plate_crop':crop,'confidence':.99,'detection_method':'TEST_FIXTURE','bbox':[0,0,240,60],'abs_bbox':[0,0,240,60]}])
    manager=ANPRManager()
    class FixedOCR:
        def readtext(self,*args): return [([], 'GJ01AB1234', .99)]
    manager.ocr_reader=FixedOCR()
    monkeypatch.setattr(manager,'_save_sighting_crop',lambda *args:None)
    frame=np.zeros((300,400,3),dtype=np.uint8)
    args=dict(camera_id='A',track_id=1,vehicle_type='car',full_frame=frame,vehicle_bbox=[0,0,300,200],session_id='test')
    first=manager.process_vehicle_crop(**args,timestamp='2026-09-05T10:00:00+00:00')
    assert first['status']!='CONFIRMED'
    manager.process_vehicle_crop(**args,timestamp='2026-09-05T10:00:00+00:00')
    assert sighting_repo.stats()['total_sightings']==0
    original=sighting_repo.record_sighting
    def fail_once(**kwargs): raise RuntimeError('Temporary write failure')
    monkeypatch.setattr(sighting_repo,'record_sighting',fail_once)
    manager.process_vehicle_crop(**args,timestamp='2026-09-05T10:00:01+00:00')
    assert not manager._persisted_tracks
    monkeypatch.setattr(sighting_repo,'record_sighting',original)
    manager.process_vehicle_crop(**args,timestamp='2026-09-05T10:00:02+00:00')
    assert sighting_repo.stats()['total_sightings']==1
    assert len(sighting_repo.list_alerts())==1
