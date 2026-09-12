"""Run the actual recorded-video worker in a new isolated evidence directory.

No reference plate strings enter inference. Evaluate the saved database separately.
"""
import argparse
import hashlib
import json
import os
import time
from pathlib import Path


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('video', type=Path)
    p.add_argument('--output', required=True, type=Path)
    p.add_argument('--engine', choices=['easyocr','plate_onnx'], default='easyocr')
    p.add_argument('--plate-format', choices=['INDIA','FINLAND_STANDARD'], default='INDIA')
    p.add_argument('--timeout', type=int, default=600)
    args = p.parse_args()
    if not args.video.is_file() or not 10 <= args.timeout <= 1800:
        p.error('Provide an existing video and a 10–1800 second timeout')
    output = args.output.resolve()
    if output.exists(): p.error('Use a new output directory to keep previous evidence intact')
    output.mkdir(parents=True)
    root = Path(__file__).resolve().parents[1]
    camera_id = 'VIDEO-VALIDATION'
    os.environ.update(CCTV_DATA_DIR=str(output/'state'), CCTV_DB_PATH=str(output/'observations.db'),
        CCTV_MEDIA_DIR=str(args.video.resolve().parent), CCTV_OCR_MODEL_DIR=str(root/'data/ocr-models'),
        ANPR_OCR_ENGINE=args.engine, ANPR_CAMERA_FORMATS=json.dumps({camera_id:args.plate_format}),
        AI_ENABLED='true', FETCH_CATALOGUE_ON_START='false', ALLOW_MODEL_DOWNLOAD='false')
    import cv2
    from app.services.sighting_repository import sighting_repo
    from app.services.stream_worker import RTSPStreamWorker
    from app.services.yolo_service import yolo_detector
    from app.services.anpr_service import anpr_manager
    if not yolo_detector.get_telemetry()['ready'] or not anpr_manager.get_telemetry()['ready']:
        raise RuntimeError('Required AI model unavailable')
    if args.engine == 'plate_onnx' and anpr_manager.ocr_engine != 'PLATE_ONNX_CCT_S_V2':
        raise RuntimeError('Requested OCR engine did not load; refusing a misleading comparison')
    capture = cv2.VideoCapture(str(args.video.resolve()))
    expected_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT)); source_fps = capture.get(cv2.CAP_PROP_FPS); capture.release()
    sighting_repo.save_cameras([{'id':camera_id,'name':'Isolated recorded-video validation',
        'source_type':'RECORDED','source_system':'PUBLIC_RECORDED_VALIDATION', 'geo_source':'UNKNOWN',
        'rtsp_url':str(args.video.resolve()),'location':'No verified location supplied'}])
    assert sighting_repo.get_camera(camera_id)['source_type'] == 'RECORDED'
    worker = RTSPStreamWorker(camera_id,str(args.video.resolve()))
    started = time.monotonic(); worker.start(); samples = []
    try:
        while worker._thread.is_alive() and time.monotonic()-started < args.timeout:
            samples.append({'elapsed_seconds':round(time.monotonic()-started,2),
                            'frames':worker.frames_received,'status':worker.status})
            if len(samples) % 10 == 0: print(json.dumps(samples[-1]),flush=True)
            time.sleep(1)
        status = worker.get_status()
        report = {'source_sha256':hashlib.sha256(args.video.read_bytes()).hexdigest(),
            'source_name':args.video.name,'camera_id':camera_id,'engine':anpr_manager.ocr_engine,
            'expected_frames':expected_frames,'source_fps':source_fps,'elapsed_seconds':round(time.monotonic()-started,2),
            'completed':status['status']=='ENDED' and worker.frames_received==expected_frames,
            'worker':status,'session_id':yolo_detector._sessions.get(camera_id),
            'ai':yolo_detector.get_telemetry(),'ocr':anpr_manager.get_telemetry(),
            'sightings':sighting_repo.list_sightings(camera_id=camera_id,limit=1000),'samples':samples,
            'scope':'Actual worker and durable observations. This is not accuracy until matched against complete independent labels; not live latency or multi-camera capacity.'}
        (output/'run.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({k:report[k] for k in ['completed','expected_frames','elapsed_seconds','engine','session_id']}),flush=True)
        if not report['completed']: raise RuntimeError('Video run incomplete; inspect run.json')
    finally:
        worker.stop(); sighting_repo.close()

if __name__ == '__main__': main()
