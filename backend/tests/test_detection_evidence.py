import csv
import io
from types import SimpleNamespace
import numpy as np
from test_acceptance import client, camera
from app.api import detections
from app.services.detection_report import detection_row
from app.services.sighting_repository import sighting_repo

def test_report_preserves_time_source_and_does_not_publish_uncertain_plate(client,monkeypatch):
    row=dict(camera_id='A',camera_name='=formula',location='Test',source_type='GOVERNMENT_REPLAY',timestamp='2026-09-11T10:00:00+00:00',timestamp_basis='PTS_ESTIMATED_UTC',media_offset_seconds=12.5,session_id='one',track_id=7,vehicle_type='car',bbox=[1,2,30,40],anpr={'plate_number':'GJ01AB1234','status':'LOW_CONFIDENCE'})
    monkeypatch.setattr(detections.stream_manager,'get_active_camera_ids',lambda:['A'])
    monkeypatch.setattr(detections.stream_manager,'get_worker',lambda cid:SimpleNamespace(get_recent_detections=lambda:[row]))
    response=client.get('/api/detections/export')
    assert response.status_code==200
    data=list(csv.DictReader(io.StringIO(response.text)))[0]
    assert data['observed_at_utc']==row['timestamp'] and data['media_offset_seconds']=='12.5'
    assert data['source_type']=='GOVERNMENT_REPLAY' and data['timestamp_basis']=='PTS_ESTIMATED_UTC'
    assert data['plate_number']=='' and data['plate_status']=='LOW_CONFIDENCE'
    assert data['camera_name']=="'=formula"
    assert 'not a complete' in response.headers['X-Report-Scope']
    assert sighting_repo.audit_history()[0]['action']=='DETECTION_EXPORT'

def test_empty_report_keeps_schema(client,monkeypatch):
    monkeypatch.setattr(detections.stream_manager,'get_active_camera_ids',lambda:[])
    response=client.get('/api/detections/export')
    assert 'observed_at_utc' in response.text and 'session_id' in response.text
    assert list(csv.DictReader(io.StringIO(response.text)))==[]

def test_only_independent_readable_frames_confirm(client,monkeypatch):
    from app.services.anpr_service import ANPRManager, modular_plate_detector
    client.post('/api/registry/cameras',json=camera('A'))
    client.post('/api/watchlist',json={'plate_number':'GJ01AB1234'})
    good=np.random.default_rng(5).integers(0,255,(60,240,3),dtype=np.uint8)
    current=[np.full((60,240,3),120,dtype=np.uint8)]
    def candidates(*a,**kw):
        h,w=current[0].shape[:2]
        return [{'plate_crop':current[0],'confidence':.99,'detection_method':'TEST','bbox':[0,0,w,h],'abs_bbox':[0,0,w,h]}]
    monkeypatch.setattr(modular_plate_detector,'detect_plates',candidates)
    manager=ANPRManager()
    class OCR:
        calls=0
        def readtext(self,*a):self.calls+=1;return [([], 'GJ01AB1234',.99)]
    manager.ocr_reader=OCR();monkeypatch.setattr(manager,'_save_sighting_crop',lambda *a:None)
    def frame(second):return manager.process_vehicle_crop(camera_id='A',track_id=1,vehicle_type='car',full_frame=np.zeros((300,400,3),dtype=np.uint8),vehicle_bbox=[0,0,300,200],session_id='quality',timestamp=f'2026-09-11T10:00:{second:02d}+00:00')
    frame(0);frame(1)
    assert manager.ocr_reader.calls==0 and sighting_repo.stats()['total_sightings']==0
    current[0]=good;frame(2)
    current[0]=np.full((60,240,3),120,dtype=np.uint8);frame(3)
    current[0]=np.zeros((5,10,3),dtype=np.uint8);frame(4)
    assert sighting_repo.stats()['total_sightings']==0
    current[0]=good
    assert frame(5)['status']=='CONFIRMED'
    assert sighting_repo.stats()['total_sightings']==1
    assert len(sighting_repo.list_alerts())==1


def test_heuristic_score_cannot_exceed_its_ceiling(monkeypatch):
    from app.services.plate_detector import HeuristicPlateDetector
    import cv2
    contour=np.array([[[10,50]],[[190,50]],[[190,95]],[[10,95]]],dtype=np.int32)
    monkeypatch.setattr(cv2,'findContours',lambda *a,**k:([contour],None))
    candidates=HeuristicPlateDetector.detect(np.zeros((100,200,3),dtype=np.uint8))
    assert candidates and candidates[0]['confidence']<=.85


def test_foreign_format_is_explicit_and_does_not_relax_indian_validation():
    from app.services.anpr_service import validate_plate_for_source
    from app.config import Settings
    import pytest
    from pydantic import ValidationError
    assert validate_plate_for_source('ZPN-720','FINLAND_STANDARD')==(True,'ZPN720',1.0)
    assert not validate_plate_for_source('ZPN-720')[0]
    assert validate_plate_for_source('GJ01AB1234')[0]
    assert not validate_plate_for_source('GJ01AB1234','FINLAND_STANDARD')[0]
    assert not validate_plate_for_source('ZPN72O','FINLAND_STANDARD')[0]
    assert not validate_plate_for_source('TRA100','UNKNOWN')[0]
    with pytest.raises(ValidationError): Settings(ANPR_CAMERA_FORMATS={'A':'ANY_TEXT'})


def test_embedded_ocr_uncertainty_is_not_deleted_into_a_valid_plate():
    from app.services.anpr_service import validate_plate_for_source
    for text in ['HT| 748','HT.748','HT/.748']:
        assert not validate_plate_for_source(text,'FINLAND_STANDARD')[0]
    assert not validate_plate_for_source('GJ01A|1234')[0]
    assert validate_plate_for_source('HT-748','FINLAND_STANDARD')[0]
    assert validate_plate_for_source('ZPN 720]','FINLAND_STANDARD')[0]
    assert validate_plate_for_source('GJ01 AB-1234')[0]


def test_short_track_split_keeps_sightings_without_repeating_alerts(client):
    for cid in ['A','B']: client.post('/api/registry/cameras',json=camera(cid))
    client.post('/api/watchlist',json={'plate_number':'GJ01AB1234'})
    def sight(cid,session,tid,offset):
        return sighting_repo.record_sighting(plate_number='GJ01AB1234',camera_id=cid,session_id=session,track_id=tid,status='CONFIRMED',media_offset_seconds=offset)
    assert sight('A','one',1,.65)['alert']
    assert sight('A','one',2,1.98)['alert'] is None
    assert sighting_repo.stats()['total_sightings']==2
    assert sight('B','one',1,1.98)['alert']
    assert sight('A','two',1,1.98)['alert']
    assert sight('A','one',3,4.0)['alert']
    assert sight('A','one',4,None)['alert']
    assert sighting_repo.stats()['total_sightings']==6
    assert len(sighting_repo.list_alerts())==5


def test_recording_completion_is_distinct_from_missing_frames():
    from app.services.stream_worker import RTSPStreamWorker
    worker=RTSPStreamWorker('TEST-STATE','unused.mp4')
    worker.status='ENDED'
    assert worker.get_health()['connection']=='ENDED'
    worker.status='CONNECTED'
    assert worker.get_health()['connection']=='FRAME_DELIVERY_ERROR'
    worker.status='DISCONNECTED'
    assert worker.get_health()['connection']=='DISCONNECTED'


def test_roi_padding_does_not_attach_a_neighboring_vehicle_plate():
    from app.services.plate_detector import ModularPlateDetector
    detector = ModularPlateDetector.__new__(ModularPlateDetector)
    detector.mode = 'vehicle_roi'
    # Vehicle is x=50..150; padded crop starts at x=40. High-score plate center
    # at x=154 belongs to a neighbor. The lower-score plate is on this vehicle.
    detector.trained_detector = SimpleNamespace(detect=lambda image: [
        {'bbox':[108,45,120,55], 'confidence':.99},
        {'bbox':[40,45,70,55], 'confidence':.8}])
    result = detector.detect_plates(np.zeros((200,220,3),dtype=np.uint8),[50,50,150,150])
    assert len(result) == 1 and result[0]['abs_bbox'] == [80,85,110,95]


def test_full_frame_fallback_keeps_plate_on_requested_vehicle():
    from app.services.plate_detector import ModularPlateDetector
    detector = ModularPlateDetector.__new__(ModularPlateDetector)
    detector.mode = 'full_frame'
    detector.trained_detector = SimpleNamespace(detect=lambda image: [
        {'bbox':[140,60,180,80], 'confidence':.99}])
    frame = np.zeros((100,220,3),dtype=np.uint8)
    assert detector.detect_plates(frame,[0,0,90,99]) == []
    assert len(detector.detect_plates(frame,[120,0,200,99])) == 1
    assert len(detector.detect_plates(frame)) == 1
