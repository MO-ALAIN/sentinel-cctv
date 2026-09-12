"""Collect actual API detections over a bounded demo window with explicit sampling limits."""
import argparse
import csv
import json
import time
from pathlib import Path
from datetime import datetime, timezone
import httpx
from app.services.detection_report import FIELDS, detection_row, event_key

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('camera_id');p.add_argument('--seconds',type=int,default=120);p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if not 5<=args.seconds<=600:p.error('Use 5 to 600 seconds')
    report={'camera_id':args.camera_id,'started_at':datetime.now(timezone.utc).isoformat(),'scope':'Actual detections collected by polling a bounded API buffer. Not independently labelled accuracy or a guaranteed complete source timeline.','samples':[],'buffer_saturation_observed':False}
    collected={}
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=10) as client:
        def get(path):
            r=client.get(path);r.raise_for_status();return r.json()
        baseline=get('/api/detections?camera_id='+args.camera_id+'&limit=500')
        seen={event_key(d) for d in baseline}
        report['baseline_events_excluded']=len(seen)
        end=time.monotonic()+args.seconds
        while time.monotonic()<end:
            sample={'checked_at':datetime.now(timezone.utc).isoformat()}
            try:
                detections=get('/api/detections?camera_id='+args.camera_id+'&limit=500')
                sample['health']=get('/api/cameras/'+args.camera_id+'/health')
                report['buffer_saturation_observed'] |= len(detections)>=100
                for d in detections:
                    key=event_key(d)
                    if key not in seen:
                        collected[key]=d;seen.add(key)
            except httpx.HTTPError as e:sample['error']=type(e).__name__
            report['samples'].append(sample)
            time.sleep(min(1,max(0,end-time.monotonic())))
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        try: report['runtime']=get('/api/system/health')
        except httpx.HTTPError as e: report['runtime_error']=type(e).__name__
    rows=sorted(collected.values(),key=lambda d:d.get('timestamp',''))
    report['detection_events']=len(rows)
    report['camera_session_tracks']=len({(d.get('camera_id'),d.get('session_id'),d.get('track_id')) for d in rows})
    report['track_count_note']='Camera/session-local track count; not independently verified distinct vehicles.'
    report['detections']=rows
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.with_suffix('.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with args.output.with_suffix('.csv').open('w',newline='',encoding='utf-8-sig') as out:
        writer=csv.DictWriter(out,fieldnames=FIELDS,extrasaction='ignore');writer.writeheader()
        for detection in rows:
            row=detection_row(detection)
            writer.writerow({k:("'"+v if isinstance(v,str) and v.lstrip().startswith(('=','+','-','@')) else v) for k,v in row.items()})
    print(json.dumps({k:report[k] for k in ['camera_id','detection_events','camera_session_tracks','buffer_saturation_observed','started_at','finished_at']},indent=2))
if __name__=='__main__':main()
