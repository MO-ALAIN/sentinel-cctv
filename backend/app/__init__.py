"""Keep model configuration and caches inside the selected project data directory."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parents[1] / ".env", override=False)
_data = Path(os.getenv('CCTV_DATA_DIR', str(Path(__file__).resolve().parents[2] / 'data')))
os.environ.setdefault('YOLO_CONFIG_DIR', str(_data / 'ultralytics'))
os.environ.setdefault('MPLCONFIGDIR', str(_data / 'matplotlib'))
os.environ.setdefault('TORCH_HOME', str(_data / 'torch'))
os.environ.setdefault('EASYOCR_MODULE_PATH', str(_data / 'easyocr'))
for _name in ('YOLO_CONFIG_DIR','MPLCONFIGDIR','TORCH_HOME','EASYOCR_MODULE_PATH'):
    Path(os.environ[_name]).mkdir(parents=True,exist_ok=True)
