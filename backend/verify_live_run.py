"""Bounded local API observation of an authorized camera; no source-video download."""
import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
import httpx

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('camera_id'); p.add_argument('--seconds',type=int,default=60)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args()
    if not 5<=args.seconds<=300: p.error('Use a bounded 5–300 second window')
    with httpx.Client(base_url='http://127.0.0.1:8000',timeout=15) as client:
        def get(path):
            r=client.get(path); r.raise_for_status(); return r.json()
        before=get('/api/system/health')
        report={'camera_id':args.camera_id,'started_at':datetime.now(timezone.utc).isoformat(),
                'scope':'Observed application runtime only; not labelled accuracy, throughput capacity or cross-camera recognition evidence.',
                'before':before,'samples':[]}
        until=time.monotonic()+args.seconds
        while time.monotonic()<until:
            report['samples'].append({'at':datetime.now(timezone.utc).isoformat(),'health':get(f'/api/cameras/{args.camera_id}/health')})
            time.sleep(min(5,max(0,until-time.monotonic())))
        report['after']=get('/api/system/health')
        report['registry']=get('/api/registry/stats')
        records=get(f'/api/anpr?camera_id={args.camera_id}&limit=500')
        report['recognition_status_counts']={status:sum(r['status']==status for r in records) for status in ['CONFIRMED','LOW_CONFIDENCE','UNREADABLE']}
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        args.output.parent.mkdir(parents=True,exist_ok=True)
        args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({'camera_id':args.camera_id,'samples':len(report['samples']),
                          'connected_samples':sum(s['health']['streaming'] for s in report['samples']),
                          'analysis_frames_delta':report['after']['ai']['total_frames_processed']-before['ai']['total_frames_processed'],
                          'recognition_status_counts':report['recognition_status_counts'],'output':str(args.output)},indent=2))

if __name__=='__main__': main()
