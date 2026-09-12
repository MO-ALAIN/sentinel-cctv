"""Probe one registered feed without exposing credentials in commands or native logs."""
import argparse
import asyncio
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from app.services.catalogue import catalogue_service

CHILD = r'''
import os,sys,json,time,math
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS']='rtsp_transport;tcp'
import cv2
source=json.loads(sys.stdin.read())
cap=cv2.VideoCapture(source,cv2.CAP_FFMPEG,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,7000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,5000])
pts=[]; shape=None; start=time.monotonic()
opened=cap.isOpened()
try:
 while opened and time.monotonic()-start<8 and len(pts)<120:
  ok,frame=cap.read()
  if ok:
   shape=list(frame.shape)
   value=cap.get(cv2.CAP_PROP_POS_MSEC)
   if math.isfinite(value): pts.append(value)
finally: cap.release()
print(json.dumps(dict(opened=opened,frames_decoded=len(pts),frame_shape=shape,
 advancing_pts=sum(b>a for a,b in zip(pts,pts[1:])),
 pts_regressions=sum(b<a for a,b in zip(pts,pts[1:])),elapsed_seconds=round(time.monotonic()-start,2))))
'''


async def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('camera_id')
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    camera=await catalogue_service.get_camera_by_id(args.camera_id)
    if not camera or not camera.get('rtsp_url'):
        parser.error('Onboard this camera before probing')
    report={'camera_id':args.camera_id,'checked_at':datetime.now(timezone.utc).isoformat(),
            'source_type':camera['source_type'],'test':'decode and advancing media timestamps; no ANPR accuracy claim'}
    try:
        process=subprocess.run([sys.executable,'-c',CHILD],input=json.dumps(camera['rtsp_url']),
                               text=True,capture_output=True,timeout=30)
        report.update(json.loads(process.stdout.strip().splitlines()[-1]))
        native=process.stderr.lower()
        report['native_error_categories']=[label for text,label in
            [('401','AUTHENTICATION_REJECTED'),('403','ACCESS_FORBIDDEN'),('timed out','NETWORK_TIMEOUT'),
             ('connection refused','CONNECTION_REFUSED'),('could not find ref','DECODE_JOIN_WARNING')]
            if text in native]
    except subprocess.TimeoutExpired:
        report.update(opened=False,frames_decoded=0,error='PROBE_TIMEOUT')
    except (ValueError,IndexError):
        report.update(opened=False,frames_decoded=0,error='PROBE_FAILED')
    finally:
        await catalogue_service.close()
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    asyncio.run(main())
