import pytest
from test_acceptance import client, camera

def feature(fid, kind, right=74, provenance='VERIFIED'):
    return {'type':'Feature','properties':dict(id=fid,name=fid,kind=kind,provenance=provenance,camera_id='A' if kind=='CAMERA' else None),
            'geometry':{'type':'Polygon','coordinates':[[[72,22],[right,22],[right,23],[72,23],[72,22]]]}}

def post(client, *features):
    return client.post('/api/registry/coverage',json={'type':'FeatureCollection','features':features})

def test_union_does_not_double_count_and_excludes_representative(client):
    client.post('/api/registry/cameras',json=camera('A'))
    assert post(client,feature('area','AREA'),feature('one','CAMERA',73),feature('overlap','CAMERA',73),feature('illustrative','CAMERA',74,'REPRESENTATIVE')).status_code==200
    report=client.get('/api/registry/coverage/gaps').json()
    assert report['status']=='MEASURED'
    assert report['areas'][0]['coverage_percent']==pytest.approx(50,abs=.01)
    assert report['areas'][0]['uncovered_geometry']['type']=='Polygon'
    assert report['excluded_representative_features']==1
    assert client.delete('/api/registry/coverage/area').status_code==200
    assert client.get('/api/registry/coverage/gaps').json()['status']=='MISSING_VERIFIED_AREA'

def test_import_is_atomic_and_validates_footprints(client):
    assert post(client,feature('area','AREA'),feature('unknown-camera','CAMERA')).status_code==422
    assert client.get('/api/registry/coverage').json()['features']==[]
    invalid=feature('invalid','AREA'); invalid['geometry']['coordinates'][0][1]=[999,22]
    assert post(client,feature('area','AREA'),invalid).status_code==422
    assert client.get('/api/registry/coverage').json()['features']==[]
    assert post(client,feature('a','AREA'),feature('a','AREA')).status_code==422

def test_viewer_can_inspect_but_cannot_change_surveys(client,monkeypatch):
    monkeypatch.setenv('CCTV_ADMIN_PASSWORD','coverage-admin-test')
    monkeypatch.setenv('CCTV_VIEWER_PASSWORD','coverage-viewer-test')
    assert client.post('/api/auth/login',json={'username':'viewer','password':'coverage-viewer-test'}).status_code==200
    assert client.get('/api/registry/coverage/gaps').status_code==200
    assert post(client,feature('area','AREA')).status_code==403
    assert client.delete('/api/registry/coverage/area').status_code==403
