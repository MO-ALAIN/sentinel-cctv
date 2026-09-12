"""Explicitly download baseline vehicle and OCR weights; never runs on server startup."""
import os
import argparse
import hashlib
import importlib
import shutil
from urllib.request import urlopen
from pathlib import Path
from app.paths import MODEL_DIR, DATA_DIR, OCR_MODEL_DIR

os.environ.setdefault('YOLO_CONFIG_DIR', str(DATA_DIR / 'ultralytics'))
os.environ.setdefault('MPLCONFIGDIR', str(DATA_DIR / 'matplotlib'))

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--plate-detector',action='store_true',help='Install the pinned third-party plate localization baseline')
    parser.add_argument('--plate-ocr',action='store_true',help='Install pinned optional CPU plate OCR model')
    args=parser.parse_args()
    from ultralytics.utils.downloads import safe_download
    from ultralytics import YOLO
    import easyocr
    import torch
    MODEL_DIR.mkdir(parents=True,exist_ok=True)
    weight = MODEL_DIR / 'yolov8n.pt'
    if not weight.exists():
        safe_download('https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8n.pt',file=weight.name,dir=weight.parent)
    YOLO(str(weight))
    if args.plate_detector:
        staged=DATA_DIR/'model-downloads'/'plate-detector.pt'
        staged.parent.mkdir(parents=True,exist_ok=True)
        if not staged.exists():
            with urlopen('https://huggingface.co/Babblu2821/alpr-plate-detector/resolve/4ae32c182f083f1a60c3a8c1a19ad82b2674eea3/best.pt',timeout=45) as response, staged.open('wb') as output:
                shutil.copyfileobj(response,output)
        if hashlib.sha256(staged.read_bytes()).hexdigest()!='f05ae9d42f9f88757670f5f333f128a64738419d746393c8c9d09c0801af6e8d':
            raise ValueError('Plate model checksum mismatch')
        approved=[]
        for name in torch.serialization.get_unsafe_globals_in_checkpoint(staged):
            if name=='builtins.set': approved.append(set);continue
            if not name.startswith(('torch.nn.','ultralytics.nn.')):
                raise ValueError('Unapproved model checkpoint type: '+name)
            module,attribute=name.rsplit('.',1)
            value=getattr(importlib.import_module(module),attribute)
            if not isinstance(value,type) or not issubclass(value,torch.nn.Module):
                raise ValueError('Checkpoint contains a non-model global')
            approved.append(value)
        with torch.serialization.safe_globals(approved):
            checkpoint=torch.load(staged,map_location='cpu',weights_only=True)
        del checkpoint
        shutil.copyfile(staged,MODEL_DIR/'license_plate_detector.pt')
        print('Pinned plate localization baseline installed; accuracy requires evaluation on target footage.')
    if args.plate_ocr:
        from app.services.plate_ocr import MODEL_HASH, CONFIG_HASH
        destination = MODEL_DIR / 'plate_ocr'
        destination.mkdir(parents=True, exist_ok=True)
        for filename, expected in [('cct_s_v2_global.onnx', MODEL_HASH), ('cct_s_v2_global_plate_config.yaml', CONFIG_HASH)]:
            target = destination / filename
            if target.is_file() and hashlib.sha256(target.read_bytes()).hexdigest() == expected:
                continue
            temporary = target.with_suffix(target.suffix + '.part')
            with urlopen('https://github.com/ankandrew/cnn-ocr-lp/releases/download/arg-plates/' + filename, timeout=45) as response, temporary.open('wb') as output:
                shutil.copyfileobj(response, output)
            if hashlib.sha256(temporary.read_bytes()).hexdigest() != expected:
                raise ValueError('Plate OCR checksum mismatch')
            temporary.replace(target)
        print('Optional plate OCR installed; select only after source-specific evaluation.')
    easyocr.Reader(['en'],gpu=torch.cuda.is_available(),model_storage_directory=str(OCR_MODEL_DIR),download_enabled=True,verbose=False)
    print('Vehicle and OCR models ready.')

if __name__ == '__main__': main()
