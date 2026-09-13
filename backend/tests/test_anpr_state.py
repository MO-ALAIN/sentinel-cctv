"""Recognition state must be bounded and must not invent confidence or alerts."""
import gc
import weakref
from types import SimpleNamespace
import numpy as np
import pytest
from test_acceptance import client, camera
from app.services.anpr_service import ANPRManager, modular_plate_detector
from app.services.sighting_repository import sighting_repo


def reader(monkeypatch, output=None):
    manager = ANPRManager()
    manager.ocr_engine = 'PLATE_ONNX_CCT_S_V2'
    manager.ocr_reader = SimpleNamespace(readtext=lambda image: output or [])
    monkeypatch.setattr(manager, '_save_sighting_crop', lambda *args: None)
    def detect(frame, **kwargs):
        return [dict(plate_crop=frame[10:70, 10:250], confidence=.99,
                     detection_method='TEST_FIXTURE', bbox=[10,10,250,70], abs_bbox=[10,10,250,70])]
    monkeypatch.setattr(modular_plate_detector, 'detect_plates', detect)
    return manager


def observe(manager, camera_id='A', track_id=1, second=0, frame=None):
    if frame is None:
        frame = np.random.default_rng(2).integers(0,255,(240,320,3),dtype=np.uint8)
    return manager.process_vehicle_crop(camera_id=camera_id, track_id=track_id,
        vehicle_type='car', full_frame=frame, vehicle_bbox=[0,0,320,240],
        timestamp=f'2026-09-13T10:00:{second:02d}+00:00', session_id='bounded-test')


def test_candidate_history_releases_original_frame_and_limits_track_state(monkeypatch):
    manager = reader(monkeypatch)
    monkeypatch.setattr(manager.settings, 'ANPR_MAX_CACHED_TRACKS', 3)
    references = []
    for tid in range(12):
        frame = np.random.default_rng(tid).integers(0,255,(1080,1920,3),dtype=np.uint8)
        references.append(weakref.ref(frame))
        observe(manager, track_id=tid, frame=frame)
        del frame
    gc.collect()
    assert all(ref() is None for ref in references)
    assert len(manager._anpr_records) == len(manager._candidate_buffers) == 3
    assert manager.get_telemetry()['cached_tracks'] == 3
    assert manager.get_telemetry()['evicted_tracks'] == 9


def test_camera_reset_does_not_clear_another_camera_with_same_prefix(monkeypatch):
    manager = reader(monkeypatch)
    observe(manager, 'A'); observe(manager, 'A_SIDE')
    manager.reset_camera('A')
    assert [r['camera_id'] for r in manager.get_records()] == ['A_SIDE']


def test_eviction_preserves_durable_history_and_does_not_repeat_alert(client, monkeypatch):
    client.post('/api/registry/cameras', json=camera('A'))
    client.post('/api/watchlist', json={'plate_number':'GJ01AB1234'})
    manager = reader(monkeypatch, [([], 'GJ01AB1234', .99)])
    monkeypatch.setattr(manager.settings, 'ANPR_MAX_CACHED_TRACKS', 1)
    observe(manager, second=0); assert observe(manager, second=1)['status'] == 'CONFIRMED'
    observe(manager, track_id=2, second=2)  # Evict track 1 from transient state.
    observe(manager, second=3); observe(manager, second=4)
    assert sighting_repo.stats()['total_sightings'] == 1
    assert len(sighting_repo.list_alerts()) == 1


@pytest.mark.parametrize('output', [
    [([], 'GJ01', .99), ([], 'AB1234', .10)],
    [([], 'GJ01AB1234', float('inf'))],
    [([], 'GJ01AB1234', float('nan'))],
    [([], 'GJ01AB1234', 1.2)],
])
def test_weak_segment_and_invalid_confidence_cannot_confirm(client, monkeypatch, output):
    client.post('/api/registry/cameras', json=camera('A'))
    manager = reader(monkeypatch, output)
    observe(manager, second=0)
    assert observe(manager, second=1)['status'] != 'CONFIRMED'
    assert sighting_repo.stats()['total_sightings'] == 0


def test_winning_plate_does_not_inherit_confidence_from_wrong_text(client, monkeypatch):
    client.post('/api/registry/cameras', json=camera('A'))
    manager = reader(monkeypatch, [([], 'GJ01ZZ9999', .99)])
    observe(manager, second=0)
    manager.ocr_reader.readtext = lambda image: [([], 'GJ01AB1234', .60)]
    observe(manager, second=1)
    result = observe(manager, second=2)
    assert result['status'] == 'CONFIRMED' and result['plate_number'] == 'GJ01AB1234'
    assert result['plate_confidence'] == pytest.approx(.594)
    assert result['best_frame_timestamp'].endswith('02+00:00')
    result['plate_number'] = 'MUTATED'
    assert manager.get_records()[0]['plate_number'] == 'GJ01AB1234'
    assert sighting_repo.list_sightings()[0]['confidence'] == pytest.approx(.594)


def test_detector_latency_counts_attempts_even_when_no_plate_is_found(monkeypatch):
    manager = reader(monkeypatch)
    monkeypatch.setattr(modular_plate_detector, 'detect_plates', lambda *a, **k: [])
    observe(manager); observe(manager, second=1)
    manager.total_det_latency_ms = 20.0
    assert manager.get_telemetry()['avg_plate_detection_latency_ms'] == 10.0
    assert manager.get_telemetry()['plate_detector_runs'] == 2
