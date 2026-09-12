import sqlite3
import pytest
from evaluate_run import score,evaluate


def test_matching_does_not_reuse_or_double_count_observations():
    events=[dict(plate_number='GJ-01 AB 1234',start_seconds=0,end_seconds=10),
            dict(plate_number='GJ01AB1234',start_seconds=0,end_seconds=2)]
    observations=[dict(id=1,plate_number='GJ01AB1234',media_offset_seconds=1),
                  dict(id=2,plate_number='GJ01AB1234',media_offset_seconds=9),
                  dict(id=3,plate_number='WRONG123',media_offset_seconds=5),
                  dict(id=4,plate_number='GJ01AB1234',media_offset_seconds=9)]
    result=score(events,observations)
    assert len(result['matches'])==2
    assert len(result['false_positive_sighting_ids'])==2
    assert 3 in result['false_positive_sighting_ids']
    assert result['missed_event_indices']==[]


def test_evaluation_is_scoped_to_confirmed_camera_session_window():
    db=sqlite3.connect(':memory:');db.row_factory=sqlite3.Row
    db.execute('CREATE TABLE plate_sightings(id,plate_number,media_offset_seconds,timestamp_basis,camera_id,session_id,status)')
    db.executemany('INSERT INTO plate_sightings VALUES(?,?,?,?,?,?,?)',[
        (1,'TEST123',1,'SOURCE_TIME','A','one','CONFIRMED'),
        (2,'WRONG',1,'SOURCE_TIME','A','two','CONFIRMED'),
        (3,'WRONG',1,'SOURCE_TIME','A','one','LOW_CONFIDENCE'),
        (4,'WRONG',50,'SOURCE_TIME','A','one','CONFIRMED')])
    window=dict(camera_id='A',session_id='one',start_seconds=0,end_seconds=10,
                events=[dict(plate_number='TEST123',start_seconds=0,end_seconds=2),
                        dict(plate_number='MISSED',start_seconds=3,end_seconds=4)])
    report=evaluate({'windows':[window]},db)
    assert report['metrics']['precision']==1
    assert report['metrics']['recall']==.5
    with pytest.raises(ValueError,match='overlap'): evaluate({'windows':[window,window]},db)
