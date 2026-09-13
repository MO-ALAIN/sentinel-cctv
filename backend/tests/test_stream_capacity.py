from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
import pytest
from test_acceptance import client, camera
from app.services import stream_manager as module


class Worker:
    def __init__(self, camera_id, rtsp_url):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self.alive = False
        self.status = 'DISCONNECTED'
        self.starts = 0
        self._thread = SimpleNamespace(is_alive=lambda: self.alive)

    def start(self):
        self.alive = True
        self.starts += 1
        self.status = 'CONNECTING'

    def stop(self):
        self.alive = False
        self.status = 'DISCONNECTED'


def manager(monkeypatch):
    monkeypatch.setattr(module, 'RTSPStreamWorker', Worker)
    value = module.MultiCameraStreamManager()
    value.max_active_cameras = 2
    return value


def test_concurrent_requests_cannot_exceed_limit(monkeypatch):
    value = manager(monkeypatch)
    def connect(index):
        try:
            return value.start_camera(str(index), 'test-source').camera_id
        except module.StreamCapacityError:
            return None
    with ThreadPoolExecutor(max_workers=8) as pool:
        admitted = [cid for cid in pool.map(connect, range(16)) if cid is not None]
    assert len(admitted) == 2
    first = value.get_worker(admitted[0])
    assert value.start_camera(admitted[0], 'test-source') is first
    assert first.starts == 1
    first.status = 'ERROR'  # A reconnecting decoder still occupies its slot.
    with pytest.raises(module.StreamCapacityError):
        value.start_camera('extra', 'test-source')
    assert value.stop_camera(admitted[1])
    value.start_camera('replacement', 'test-source')
    assert value.get_capacity()['active_workers'] == 2


def test_finished_recording_releases_slot_and_failed_start_does_not_leak(monkeypatch):
    value = manager(monkeypatch)
    a = value.start_camera('A', 'recording')
    value.start_camera('B', 'network')
    a.alive = False
    a.status = 'ENDED'
    value.start_camera('C', 'network')
    with pytest.raises(module.StreamCapacityError):
        value.start_camera('A', 'recording')
    value.stop_camera('C')
    assert value.start_camera('A', 'recording') is a and a.starts == 2
    value.stop_camera('A')
    def fail(self):
        raise RuntimeError('Thread failed to start')
    monkeypatch.setattr(Worker, 'start', fail)
    with pytest.raises(RuntimeError):
        value.start_camera('failure', 'test-source')
    assert value.get_worker('failure') is None
    assert value.get_capacity()['available_slots'] == 1


def test_capacity_rejection_is_clear_before_connect_or_stream_headers(client, monkeypatch):
    from app.api import cameras, detections
    from app.services.sighting_repository import sighting_repo
    client.app.include_router(cameras.router)
    client.post('/api/registry/cameras', json=camera('A'))
    async def lookup(cid):
        return {'id': cid, 'rtsp_url': 'rtsp://camera.test/feed'}
    monkeypatch.setattr(cameras.catalogue_service, 'get_camera_by_id', lookup)
    def reject(*args):
        raise module.StreamCapacityError('Camera limit reached (2). Disconnect another camera before connecting this one.')
    monkeypatch.setattr(cameras.stream_manager, 'start_camera', reject)
    monkeypatch.setattr(detections.stream_manager, 'get_worker', lambda cid: None)
    for method, endpoint in [('POST','/api/cameras/A/connect'), ('GET','/api/cameras/A/annotated')]:
        response = client.request(method, endpoint)
        assert response.status_code == 409
        assert 'Disconnect another camera' in response.json()['detail']
    assert not sighting_repo.get_camera('A')['desired_connected']
