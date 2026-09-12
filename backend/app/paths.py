"""Stable paths shared by the synchronous repository, API and video workers."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("CCTV_DATA_DIR", str(ROOT / "data"))).resolve()
DB_PATH = Path(os.getenv("CCTV_DB_PATH", str(ROOT / "cctv_surveillance.db"))).resolve()
MEDIA_DIR = Path(os.getenv("CCTV_MEDIA_DIR", str(ROOT / "scratch"))).resolve()
EVIDENCE_DIR = DATA_DIR / "evidence"
DEMO_DIR = Path(os.getenv("CCTV_DEMO_DIR", str(ROOT / "demo_videos"))).resolve()
MODEL_DIR = Path(os.getenv("CCTV_MODEL_DIR", str(ROOT / "backend" / "app" / "models"))).resolve()
OCR_MODEL_DIR = Path(os.getenv("CCTV_OCR_MODEL_DIR", str(DATA_DIR / "ocr-models"))).resolve()

def ensure_directories():
    for path in (DATA_DIR, DB_PATH.parent, EVIDENCE_DIR):
        path.mkdir(parents=True, exist_ok=True)

def contained_file(base: Path, value: str) -> Path:
    path = (base / value).resolve()
    if not path.is_relative_to(base.resolve()):
        raise ValueError("File must be inside the configured media/evidence directory")
    return path
