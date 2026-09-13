import threading
from concurrent.futures import ThreadPoolExecutor
from test_acceptance import client
from app.api import cameras


def test_reading_empty_diagnostics_never_starts_capture(client, monkeypatch):
    client.app.include_router(cameras.router)
    monkeypatch.setattr(cameras.anpr_diagnostic_service, 'latest_diagnostics', {})
    async def forbidden(*args, **kwargs):
        raise AssertionError('Reading results must not start camera capture')
    async def lookup(cid):
        return {'id': cid}
    monkeypatch.setattr(cameras.anpr_diagnostic_service, 'run_diagnostics_selected', forbidden)
    monkeypatch.setattr(cameras.anpr_diagnostic_service, 'diagnose_camera', forbidden)
    monkeypatch.setattr(cameras.catalogue_service, 'get_camera_by_id', lookup)
    assert client.get('/api/cameras/anpr-diagnostic').json()['status'] == 'NOT_RUN'
    assert client.get('/api/cameras/anpr-diagnostic/A').json()['status'] == 'NOT_RUN'


def test_diagnostic_does_not_block_other_requests_or_allow_overlapping_jobs(client, monkeypatch):
    client.app.include_router(cameras.router)
    entered, release = threading.Event(), threading.Event()
    async def slow(*args, **kwargs):
        entered.set()
        assert release.wait(5), 'test did not release diagnostic'
        return {'status': 'COMPLETED'}
    monkeypatch.setattr(cameras.anpr_diagnostic_service, 'is_running', False)
    monkeypatch.setattr(cameras.anpr_assessor, 'is_running', False)
    monkeypatch.setattr(cameras.anpr_diagnostic_service, 'run_diagnostics_selected', slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        job = pool.submit(client.post, '/api/cameras/anpr-diagnostic/run?camera_id=A&duration=10')
        try:
            assert entered.wait(2)
            assert pool.submit(client.get, '/api/cameras/anpr-status').result(timeout=1).status_code == 200
            duplicate = pool.submit(client.post, '/api/cameras/anpr-assessment/run?camera_id=A').result(timeout=1)
            assert duplicate.status_code == 409
        finally:
            release.set()
        assert job.result(timeout=2).json()['status'] == 'COMPLETED'


def test_viewer_cannot_start_camera_diagnostics(client, monkeypatch):
    client.app.include_router(cameras.router)
    def reject(request, role):
        from fastapi import HTTPException
        assert role == 'operator'
        raise HTTPException(403, 'Operator role required')
    monkeypatch.setattr(cameras, 'require_role', reject)
    assert client.post('/api/cameras/anpr-diagnostic/run').status_code == 403
    assert client.post('/api/cameras/anpr-assessment/run').status_code == 403


def test_reading_recognition_during_ocr_does_not_block_status(client, monkeypatch):
    from app.api import anpr
    client.app.include_router(anpr.router)
    entered, release = threading.Event(), threading.Event()
    def slow(**kwargs):
        entered.set()
        assert release.wait(5)
        return []
    monkeypatch.setattr(anpr.anpr_manager, 'get_records', slow)
    with ThreadPoolExecutor(max_workers=2) as pool:
        records = pool.submit(client.get, '/api/anpr')
        try:
            assert entered.wait(2)
            assert pool.submit(client.get, '/api/anpr/stats').result(timeout=1).status_code == 200
        finally:
            release.set()
        assert records.result(timeout=2).status_code == 200
