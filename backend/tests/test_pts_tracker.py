from types import SimpleNamespace
import numpy as np
import pytest
from ultralytics.engine.results import Boxes
from app.services.pts_tracker import PTSByteTracker

def tracker():
    return PTSByteTracker(SimpleNamespace(track_high_thresh=.25,track_low_thresh=.1,new_track_thresh=.25,track_buffer=30,match_thresh=.8,fuse_score=True),timeout_seconds=10)

def boxes(present=True):
    data=np.array([[10,10,80,80,.99,2]],dtype=np.float32) if present else np.empty((0,6),dtype=np.float32)
    return Boxes(data,(100,100))

def test_expiry_uses_elapsed_media_seconds_not_number_of_updates():
    t=tracker(); frame=np.zeros((100,100,3),dtype=np.uint8)
    first=t.update_at(boxes(),frame,0); identity=int(first[0,4])
    for pts in np.linspace(.01,1,50):
        assert int(t.update_at(boxes(),frame,float(pts))[0,4])==identity
    t.update_at(boxes(False),frame,5)
    assert any(track.track_id==identity for track in t.lost_stracks)
    t.update_at(boxes(False),frame,12)
    assert not t.lost_stracks and not t.tracked_stracks
    with pytest.raises(ValueError): t.update_at(boxes(),frame,12)

def test_filters_use_independent_media_steps():
    a,b=tracker(),tracker(); frame=np.zeros((100,100,3),dtype=np.uint8)
    a.update_at(boxes(),frame,0); b.update_at(boxes(),frame,0)
    a.update_at(boxes(),frame,.2); b.update_at(boxes(),frame,2)
    assert a.kalman_filter._motion_mat[0,4]==.2
    assert b.kalman_filter._motion_mat[0,4]==2
