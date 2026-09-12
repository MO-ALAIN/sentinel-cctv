from datetime import datetime, timezone
import numpy as np
import pytest
from app.services.frame_clock import FrameClock, SceneBoundary
from app.services.traffic_analytics import CameraTrafficAnalytics


def test_pts_ignores_arrival_burst_and_resets_on_loop():
    clock = FrameClock()
    arrival = datetime(2026,9,6,tzinfo=timezone.utc)
    first = clock.observe(10000,arrival)
    second = clock.observe(11000,arrival)  # Both delivered at the same wall-clock instant.
    assert second['delta_seconds'] == 1
    assert datetime.fromisoformat(second['timestamp']).timestamp()-datetime.fromisoformat(first['timestamp']).timestamp() == 1
    assert second['timestamp_basis'] == 'PTS_ESTIMATED_UTC'
    assert clock.observe(11000) is None
    assert clock.observe(float('nan')) is None
    assert clock.observe(-1) is None
    assert clock.observe(0,arrival)['discontinuity']


def test_explicit_source_origin_and_scene_boundary():
    clock=FrameClock('2026-09-06T00:00:00+00:00')
    result=clock.observe(2500)
    assert result['timestamp']=='2026-09-06T00:00:02.500000+00:00'
    assert result['timestamp_basis']=='SOURCE_TIME'
    cut=SceneBoundary()
    assert not cut.observe(np.zeros((48,48,3),dtype=np.uint8))
    assert cut.observe(np.full((48,48,3),255,dtype=np.uint8))


def test_stationary_duration_uses_media_time():
    analytics=CameraTrafficAnalytics('TEST')
    det=[dict(track_id=1,vehicle_type='car',bbox=[10,10,100,100])]
    analytics.update(det,current_time=1000)
    analytics.update(det,current_time=1001)
    result=analytics.update(det,current_time=1062)
    assert result['stationary_vehicles'][0]['stationary_duration_seconds']==61
    assert result['flow_metrics']['vehicles_per_minute']==pytest.approx(1.0)
