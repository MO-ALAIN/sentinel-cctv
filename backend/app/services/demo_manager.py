import os
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
from app.services.demo_stream_worker import DemoStreamWorker

logger = logging.getLogger(__name__)

from app.paths import DEMO_DIR
METADATA_FILE = DEMO_DIR / "metadata.json"
QUALITY_REPORT_FILE = DEMO_DIR / "quality_report.json"

DEFAULT_DEMO_METADATA = [
    {
        "id": "CAM-DEMO-01",
        "source_type": "DEMO_MP4",
        "name": "Traffic Scenario 01",
        "scenario": "Dense Multi-Lane Traffic",
        "type": "Dense Congestion",
        "anpr_capability": "Medium Quality",
        "source": "VisDrone Dataset",
        "video_filename": "cam_demo_01.mp4",
        "mode": "DEMO",
        "recorded": True,
        "location": None,
        "display_location": "Recorded Dataset Footage",
        "status": "READY"
    },
    {
        "id": "CAM-DEMO-02",
        "source_type": "DEMO_MP4",
        "name": "Traffic Scenario 02",
        "scenario": "Urban Arterial Corridor",
        "type": "Normal Traffic",
        "anpr_capability": "High Quality",
        "source": "VisDrone Dataset",
        "video_filename": "cam_demo_02.mp4",
        "mode": "DEMO",
        "recorded": True,
        "location": None,
        "display_location": "Recorded Dataset Footage",
        "status": "READY"
    },
    {
        "id": "CAM-DEMO-03",
        "source_type": "DEMO_MP4",
        "name": "Traffic Scenario 03",
        "scenario": "Major Roundabout Junction",
        "type": "Heavy Traffic",
        "anpr_capability": "Medium Quality",
        "source": "VisDrone Dataset",
        "video_filename": "cam_demo_03.mp4",
        "mode": "DEMO",
        "recorded": True,
        "location": None,
        "display_location": "Recorded Dataset Footage",
        "status": "READY"
    },
    {
        "id": "CAM-DEMO-04",
        "source_type": "DEMO_MP4",
        "name": "Traffic Scenario 04",
        "scenario": "Commercial Hub Mixed Mobility",
        "type": "Multi-Class",
        "anpr_capability": "Low Quality (Wide Angle)",
        "source": "VisDrone Dataset",
        "video_filename": "cam_demo_04.mp4",
        "mode": "DEMO",
        "recorded": True,
        "location": None,
        "display_location": "Recorded Dataset Footage",
        "status": "READY"
    },
    {
        "id": "CAM-DEMO-05",
        "source_type": "DEMO_MP4",
        "name": "Traffic Scenario 05",
        "scenario": "High Speed Corridor",
        "type": "ANPR High Quality",
        "source": "VisDrone Dataset",
        "video_filename": "cam_demo_05.mp4",
        "mode": "DEMO",
        "recorded": True,
        "location": None,
        "display_location": "Recorded Dataset Footage",
        "status": "READY"
    },
    {
        "id": "CAM-DEMO-06",
        "source_type": "DEMO_MP4",
        "name": "Traffic Scenario 06",
        "scenario": "Perimeter Entrance Gate",
        "type": "Complex Angle",
        "source": "VisDrone Dataset",
        "video_filename": "cam_demo_06.mp4",
        "mode": "DEMO",
        "recorded": True,
        "location": None,
        "display_location": "Recorded Dataset Footage",
        "status": "READY"
    }
]

class DemoCameraManager:
    """
    Manages background DemoStreamWorker instances for VisDrone MP4 demo scenarios.
    100% isolated from Government RTSP workers.
    """
    def __init__(self):
        self.workers: Dict[str, DemoStreamWorker] = {}
        self.metadata_cache: List[Dict[str, Any]] = []
        self.active_scenario_id: str = "CAM-DEMO-01"
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return

        logger.info("Initializing DemoCameraManager with VisDrone dataset MP4 videos...")
        metadata = self._load_metadata()
        self.metadata_cache = metadata

        for item in metadata:
            cam_id = item["id"]
            video_name = item.get("video_filename", f"{cam_id.lower().replace('-', '_')}.mp4")
            video_path = str(DEMO_DIR / video_name)

            worker = DemoStreamWorker(
                camera_id=cam_id,
                video_path=video_path,
                name=item.get("name", f"Traffic Scenario {cam_id[-2:]}"),
                scenario=item.get("scenario", "VisDrone Traffic Demonstration"),
                camera_type=item.get("type", "Normal Traffic"),
                anpr_capability=item.get("anpr_capability", "Standard Quality")
            )
            self.workers[cam_id] = worker
            if os.path.isfile(video_path):
                worker.start()
            else:
                worker.status = "ERROR"
                worker.error_message = "Recording not installed; add this source through the registry"

        self._initialized = True
        logger.info(f"DemoCameraManager initialized {len(self.workers)} VisDrone demo workers.")

    def _load_metadata(self) -> List[Dict[str, Any]]:
        if os.path.exists(METADATA_FILE):
            try:
                with open(METADATA_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error reading demo metadata file: {e}")
        return DEFAULT_DEMO_METADATA

    def set_active_scenario(self, camera_id: str) -> bool:
        if camera_id in self.workers:
            self.active_scenario_id = camera_id
            for cid, worker in self.workers.items():
                worker.set_active_focus(cid == camera_id)
            return True
        return False

    def get_all_cameras(self) -> List[Dict[str, Any]]:
        if not self._initialized:
            self.initialize()
        results = []
        for cam_id, worker in self.workers.items():
            health = worker.get_health()
            health["is_selected_active"] = (cam_id == self.active_scenario_id)
            results.append(health)
        return results

    def get_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        if not self._initialized:
            self.initialize()
        worker = self.workers.get(camera_id)
        if worker:
            health = worker.get_health()
            health["is_selected_active"] = (camera_id == self.active_scenario_id)
            return health
        return None

    def get_stream_worker(self, camera_id: str) -> Optional[DemoStreamWorker]:
        if not self._initialized:
            self.initialize()
        return self.workers.get(camera_id)

    def get_quality_report(self) -> Dict[str, Any]:
        if os.path.exists(QUALITY_REPORT_FILE):
            try:
                with open(QUALITY_REPORT_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading quality report: {e}")
        return {"status": "Quality report pending or unavailable"}

    def shutdown(self):
        logger.info("Shutting down all DemoStreamWorker instances...")
        for worker in self.workers.values():
            worker.stop()
        self.workers.clear()
        self._initialized = False

# Global singleton
demo_camera_manager = DemoCameraManager()
