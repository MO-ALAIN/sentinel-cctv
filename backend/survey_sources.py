"""Bounded authorized stream survey. Saves one decoded still per camera, never source files."""
import argparse
import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path
from datetime import datetime,timezone
from app.services.catalogue import catalogue_service

CAPTURE = r"""
import sys,json,time,os,math
os.environ['OPENCV_FFMPEG_CAPTURE_OPTIONS']='rtsp_transport;tcp'
import cv2
args=json.loads(sys.stdin.read())
cap=cv2.VideoCapture(args['source'],cv2.CAP_FFMPEG,[cv2.CAP_PROP_OPEN_TIMEOUT_MSEC,7000,cv2.CAP_PROP_READ_TIMEOUT_MSEC,5000])
opened=cap.isOpened();start=time.monotonic();count=0;last=None;pts=[]
while opened and time.monotonic()-start<18:
 ok,frame=cap.read()
 if ok and frame is not None:
  count+=1;last=frame;value=cap.get(cv2.CAP_PROP_POS_MSEC)
  if math.isfinite(value):pts.append(value)
  if count>=45:break
cap.release()
saved=bool(last is not None and cv2.imwrite(args['output'],last))
print(json.dumps(dict(opened=opened,frames_decoded=count,shape=list(last.shape) if last is not None else None,advancing_pts=sum(b>a for a,b in zip(pts,pts[1:])),still_saved=saved,elapsed_seconds=round(time.monotonic()-start,2))))
"""
async def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('cameras',nargs='+');p.add_argument('--output',type=Path,required=True);args=p.parse_args()
 args.output.mkdir(parents=True,exist_ok=True);reports=[]
 try:
  for cid in args.cameras:
   if not re.fullmatch('[A-Za-z0-9_-]{1,64}',cid):p.error('Invalid camera ID')
   cam=await catalogue_service.get_camera_by_id(cid)
   if not cam:continue
   report={'camera_id':cid,'camera_name':cam['name'],'checked_at':datetime.now(timezone.utc).isoformat(),'scope':'One still and decode test; not recognition accuracy or continuous availability.'}
   try:
    result=subprocess.run([sys.executable,'-c',CAPTURE],input=json.dumps({'source':cam['rtsp_url'],'output':str((args.output/(cid+'.jpg')).resolve())}),capture_output=True,text=True,timeout=35)
    report.update(json.loads(result.stdout.strip().splitlines()[-1]))
   except subprocess.TimeoutExpired:report['error']='TIMEOUT'
   except (ValueError,IndexError):report['error']='DECODE_FAILED'
   reports.append(report);(args.output/'survey.json').write_text(json.dumps(reports,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
 finally:await catalogue_service.close()
if __name__=='__main__':asyncio.run(main())
