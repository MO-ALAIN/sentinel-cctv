"""Prepare repeatable synthetic browser data in one fixed, isolated test database."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'backend'))
FIXTURE_DB = ROOT.parent / '.test-runtime' / 'browser.db'
os.environ['CCTV_DB_PATH'] = str(FIXTURE_DB)
os.environ['AI_ENABLED'] = 'false'

from app.services.sighting_repository import SightingRepository


def main():
    FIXTURE_DB.parent.mkdir(parents=True, exist_ok=True)
    repo = SightingRepository(str(FIXTURE_DB))
    repo.save_cameras([
        dict(id=cid, name='Synthetic camera '+cid, location='Browser test fixture',
             lat=lat, lon=lon, geo_source='REPRESENTATIVE', department='TEST',
             source_system='Synthetic browser fixture', source_type='RECORDED')
        for cid, lat, lon in [('TEST-A',22.3,73.1),('TEST-B',22.35,73.15)]
    ], 'browser fixture')
    repo.add_watchlist(plate_number='TEST123', reason='STOLEN', severity='HIGH',
                         description='Synthetic browser fixture; not an official record')
    for cid, stamp in [('TEST-A','2026-09-05T10:00:00Z'),('TEST-B','2026-09-05T10:05:00Z')]:
        repo.record_sighting(plate_number='TEST123', camera_id=cid, track_id=1,
                             session_id='browser-fixture', status='CONFIRMED',
                             confidence=.9, sighted_at=stamp)
    with repo._connect() as conn:
        conn.execute("UPDATE alerts SET acknowledged=0 WHERE sighting_id IN "
                     "(SELECT id FROM plate_sightings WHERE session_id='browser-fixture')")
    repo.close()
    print(f'Synthetic browser fixtures ready: {FIXTURE_DB}')


if __name__ == '__main__':
    main()
