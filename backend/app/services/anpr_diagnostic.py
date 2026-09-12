import os
import time
import logging
import cv2
import numpy as np
try:
    import torch
except ImportError:
    torch = None
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.services.catalogue import catalogue_service
from app.services.yolo_service import yolo_detector
from app.services.plate_detector import modular_plate_detector, TrainedPlateDetector, HeuristicPlateDetector
from app.services.anpr_service import anpr_manager, MultiVariantOCRPreprocessor, IndianPlateValidator, MIN_PLATE_WIDTH, MIN_PLATE_HEIGHT

logger = logging.getLogger(__name__)

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

MAX_DIAGNOSTIC_TRACKS_PER_CAMERA = 20

class ANPRDiagnosticService:
    """
    Phase 7.7 Service: Government CCTV Plate Visibility Diagnostic & Real ANPR Validation.
    Performs empirical ANPR diagnostics, collects best vehicle/plate crops, tests primary vs fallback detectors,
    runs multi-variant OCR ensemble, tracks diagnostic failure reasons, and assigns real-world capability classifications.
    """
    def __init__(self):
        self.settings = get_settings()
        self.is_running: bool = False
        self.latest_diagnostics: Dict[str, Any] = {}

    def classify_camera(
        self,
        confirmed_plates: List[str],
        valid_reads: int,
        good_for_ocr: int,
        total_candidates: int,
        vehicles_detected: int
    ) -> str:
        """
        Classifies camera suitability based on REAL empirical ANPR evidence:
        - CONFIRMED_ANPR_CAPABLE: At least one confirmed valid plate read.
        - POTENTIAL_ANPR_CAPABLE: Good plate candidates detected & OCR attempted.
        - VEHICLE_ANALYTICS_ONLY: Vehicles detected and tracked, but plates unreadable.
        - UNSUITABLE: Poor quality or no vehicles detected.
        """
        if len(confirmed_plates) > 0 or valid_reads > 0:
            return "CONFIRMED_ANPR_CAPABLE"
        elif good_for_ocr > 0 or total_candidates > 0:
            return "POTENTIAL_ANPR_CAPABLE"
        elif vehicles_detected > 0:
            return "VEHICLE_ANALYTICS_ONLY"
        else:
            return "UNSUITABLE"

    async def diagnose_camera(
        self,
        cam_info: Dict[str, Any],
        duration_seconds: int = 45,
        sample_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Run deep ANPR diagnostic on a single camera feed:
        1. Ingest RTSP stream and track vehicles using CUDA YOLO + ByteTrack.
        2. Save best vehicle crop per track to scratch/diagnostics/{camera_id}/vehicles/
        3. Test Primary Trained Detector vs Secondary Fallback Detector separately.
        4. Save best plate crop per track to scratch/diagnostics/{camera_id}/plates/
        5. Run Multi-Variant EasyOCR on GOOD_FOR_OCR candidates.
        6. Apply Indian Format Validation & Position-Aware Character Corrections.
        7. Save visual summary diagnostic image to scratch/diagnostics/{camera_id}/summary.jpg
        """
        cam_id = cam_info["id"]
        cam_name = cam_info["name"]
        rtsp_url = cam_info["rtsp_url"]

        logger.info(f"Starting ANPR Diagnostic on camera {cam_id} ({cam_name}) for {duration_seconds}s...")

        # Setup Diagnostic Image Directories
        scratch_base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scratch", "diagnostics", cam_id)
        vehicles_dir = os.path.join(scratch_base, "vehicles")
        plates_dir = os.path.join(scratch_base, "plates")
        os.makedirs(vehicles_dir, exist_ok=True)
        os.makedirs(plates_dir, exist_ok=True)

        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        if not cap.isOpened():
            logger.warning(f"Camera {cam_id} connection FAILED or OFFLINE.")
            return {
                "camera_id": cam_id,
                "camera_name": cam_name,
                "rtsp_status": "OFFLINE",
                "frames_processed": 0,
                "vehicles_detected": 0,
                "unique_tracks": 0,
                "vehicle_crops_analysed": 0,
                "primary_plate_detections": 0,
                "fallback_plate_detections": 0,
                "total_plate_candidates": 0,
                "good_for_ocr": 0,
                "too_small": 0,
                "motion_blur": 0,
                "low_contrast": 0,
                "invalid_shape": 0,
                "ocr_failed": 0,
                "ocr_attempts": 0,
                "valid_plate_reads": 0,
                "confirmed_plates": [],
                "best_plate_resolution": "0x0",
                "best_plate_sharpness": 0.0,
                "classification": "UNSUITABLE",
                "summary_image": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        frames_processed = 0
        yolo_runs = 0
        vehicles_detected = 0
        track_map: Dict[int, Dict[str, Any]] = {}

        primary_plate_detections = 0
        fallback_plate_detections = 0
        total_plate_candidates = 0

        good_for_ocr_count = 0
        too_small_count = 0
        motion_blur_count = 0
        low_contrast_count = 0
        invalid_shape_count = 0
        ocr_failed_count = 0

        ocr_attempts = 0
        valid_plate_reads = 0
        confirmed_plates_list = []
        consensus_map: Dict[str, int] = {}

        best_pw, best_ph = 0, 0
        best_sharpness = 0.0
        representative_frame = None

        start_time = time.time()
        while (time.time() - start_time) < duration_seconds:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            frames_processed += 1
            if frames_processed % sample_interval == 0:
                yolo_runs += 1

                # CUDA YOLO Vehicle Detection + ByteTrack
                res = yolo_detector.track_vehicles(frame, cam_id)
                dets = res["detections"]
                annotated = res["annotated_frame"]
                vehicles_detected += len(dets)

                if representative_frame is None and len(dets) > 0:
                    representative_frame = annotated.copy()

                # Process tracked vehicles
                for d in dets:
                    track_id = d.get("track_id")
                    vehicle_type = d.get("vehicle_type", "car")
                    bbox = d.get("bbox")

                    if track_id is None:
                        continue

                    x1, y1, x2, y2 = bbox
                    vx1, vy1 = max(0, x1), max(0, y1)
                    vx2, vy2 = min(frame.shape[1], x2), min(frame.shape[0], y2)
                    vw, vh = vx2 - vx1, vy2 - vy1

                    if vw < 30 or vh < 30:
                        continue

                    vcrop = frame[vy1:vy2, vx1:vx2]
                    vsharp, vcontrast = MultiVariantOCRPreprocessor.compute_metrics(vcrop)
                    vquality = vvw_score = (vw * vh) * d["confidence"] * (vsharp / 100.0)

                    # Update best vehicle crop per track (up to MAX_DIAGNOSTIC_TRACKS_PER_CAMERA)
                    if track_id not in track_map and len(track_map) < MAX_DIAGNOSTIC_TRACKS_PER_CAMERA:
                        track_map[track_id] = {
                            "vehicle_type": vehicle_type,
                            "best_quality": vquality,
                            "vehicle_crop": vcrop.copy(),
                            "vehicle_bbox": [vx1, vy1, vx2, vy2],
                            "plate_evaluated": False
                        }
                    elif track_id in track_map and vquality > track_map[track_id]["best_quality"]:
                        track_map[track_id]["best_quality"] = vquality
                        track_map[track_id]["vehicle_crop"] = vcrop.copy()
                        track_map[track_id]["vehicle_bbox"] = [vx1, vy1, vx2, vy2]

        cap.release()

        # Step 1: Save Best Vehicle Crop & Run Diagnostics
        for tid, tinfo in track_map.items():
            vcrop = tinfo["vehicle_crop"]
            vtype = tinfo["vehicle_type"]
            vbbox = tinfo["vehicle_bbox"]

            # Save vehicle crop image
            vcrop_filename = f"{cam_id}_track_{tid}_{vtype}.jpg"
            vcrop_path = os.path.join(vehicles_dir, vcrop_filename)
            cv2.imwrite(vcrop_path, vcrop)

            # Step 2: Primary vs Fallback Plate Detector Diagnostics
            primary_cands = modular_plate_detector.trained_detector.detect(vcrop)
            if primary_cands:
                primary_plate_detections += len(primary_cands)
                cands = primary_cands
            else:
                fallback_cands = HeuristicPlateDetector.detect(vcrop)
                if fallback_cands:
                    fallback_plate_detections += len(fallback_cands)
                    cands = fallback_cands
                else:
                    cands = []

            if not cands:
                continue

            total_plate_candidates += len(cands)
            top_plate = cands[0]
            pcrop = top_plate["plate_crop"]
            ph, pw = pcrop.shape[:2]

            if pw > best_pw:
                best_pw = pw
                best_ph = ph

            psharp, pcontrast = MultiVariantOCRPreprocessor.compute_metrics(pcrop)
            if psharp > best_sharpness:
                best_sharpness = psharp

            # Save plate diagnostic crop image
            pcrop_filename = f"{cam_id}_track_{tid}_plate.jpg"
            pcrop_path = os.path.join(plates_dir, pcrop_filename)
            cv2.imwrite(pcrop_path, pcrop)

            # Step 2 & 4: Candidate Quality Pre-Check & Multi-Variant OCR Execution
            if pw < MIN_PLATE_WIDTH or ph < MIN_PLATE_HEIGHT:
                too_small_count += 1
            elif psharp < 20.0:
                motion_blur_count += 1
            elif pcontrast < 12.0:
                low_contrast_count += 1
            elif float(pw) / float(ph) < 1.8 or float(pw) / float(ph) > 6.5:
                invalid_shape_count += 1
            else:
                good_for_ocr_count += 1
                ocr_attempts += 1

                # Step 4: Multi-Variant OCR Ensemble
                variants = MultiVariantOCRPreprocessor.generate_variants(pcrop)
                best_valid_read = None

                for var in variants:
                    try:
                        ocr_out = anpr_manager.ocr_reader.readtext(var["image"])
                        if ocr_out:
                            raw_txt = " ".join([r[1] for r in ocr_out if len(r) >= 2])
                            conf_parts = [r[2] for r in ocr_out if len(r) >= 3]
                            ocr_conf = float(np.mean(conf_parts)) if conf_parts else 0.5

                            is_valid, corrected_plate, val_score = IndianPlateValidator.validate(raw_txt)

                            if is_valid and ocr_conf >= 0.40 and len(corrected_plate) >= 6:
                                best_valid_read = corrected_plate
                                break
                    except Exception as e:
                        logger.error(f"Diagnostic OCR error: {e}")

                if best_valid_read:
                    valid_plate_reads += 1
                    consensus_map[best_valid_read] = consensus_map.get(best_valid_read, 0) + 1
                else:
                    ocr_failed_count += 1

        # Determine confirmed plates (supported by OCR evidence)
        for plate_str, count in consensus_map.items():
            if plate_str not in confirmed_plates_list:
                confirmed_plates_list.append(plate_str)

        # Step 5: Real ANPR Success Classification
        classification = self.classify_camera(
            confirmed_plates=confirmed_plates_list,
            valid_reads=valid_plate_reads,
            good_for_ocr=good_for_ocr_count,
            total_candidates=total_plate_candidates,
            vehicles_detected=vehicles_detected
        )

        # Visual Summary Diagnostic Image
        summary_img_path = None
        if representative_frame is None and frame is not None:
            representative_frame = frame.copy()

        if representative_frame is not None:
            disp = representative_frame.copy()
            # Overlay Diagnostic Banner
            header_text = f"CAM: {cam_id.upper()} | REAL ANPR STATUS: {classification}"
            detail_text = f"Vehicles: {len(track_map)} | Candidates: {total_plate_candidates} | Good OCR: {good_for_ocr_count} | Valid Reads: {valid_plate_reads}"

            cv2.rectangle(disp, (0, 0), (750, 48), (0, 0, 0), -1)
            cv2.putText(disp, header_text, (10, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(disp, detail_text, (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (255, 255, 255), 1, cv2.LINE_AA)

            summary_img_path = os.path.join(scratch_base, "summary.jpg")
            cv2.imwrite(summary_img_path, disp)

        diagnostic_result = {
            "camera_id": cam_id,
            "camera_name": cam_name,
            "rtsp_status": "ONLINE",
            "frames_processed": frames_processed,
            "vehicles_detected": vehicles_detected,
            "unique_tracks": len(track_map),
            "vehicle_crops_analysed": len(track_map),
            "primary_plate_detections": primary_plate_detections,
            "fallback_plate_detections": fallback_plate_detections,
            "total_plate_candidates": total_plate_candidates,
            "good_for_ocr": good_for_ocr_count,
            "too_small": too_small_count,
            "motion_blur": motion_blur_count,
            "low_contrast": low_contrast_count,
            "invalid_shape": invalid_shape_count,
            "ocr_failed": ocr_failed_count,
            "ocr_attempts": ocr_attempts,
            "valid_plate_reads": valid_plate_reads,
            "confirmed_plates": confirmed_plates_list,
            "best_plate_resolution": f"{best_pw}x{best_ph}",
            "best_plate_sharpness": round(best_sharpness, 1),
            "classification": classification,
            "summary_image": summary_img_path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

        self.latest_diagnostics[cam_id] = diagnostic_result
        return diagnostic_result

    async def run_diagnostics_selected(
        self,
        camera_ids: Optional[List[str]] = None,
        duration_per_camera: int = 45
    ) -> Dict[str, Any]:
        """
        Run Phase 7.7 ANPR Diagnostics sequentially across specified or recommended cameras.
        """
        if self.is_running:
            logger.warning("ANPR Diagnostic job is already running.")
            return {"status": "ALREADY_RUNNING", "message": "Diagnostic job in progress."}

        self.is_running = True
        logger.info("Starting Phase 7.7 ANPR Diagnostic Job...")

        try:
            catalogue = await catalogue_service.fetch_catalogue()
            if camera_ids:
                catalogue = [c for c in catalogue if c["id"] in camera_ids]

            results = []
            for cam_info in catalogue:
                res = await self.diagnose_camera(cam_info, duration_seconds=duration_per_camera)
                results.append(res)

            # Step 7: Final Camera Ranking based on REAL ANPR Performance
            results.sort(key=lambda r: (
                len(r["confirmed_plates"]),
                r["valid_plate_reads"],
                r["good_for_ocr"],
                r["total_plate_candidates"],
                int(r["best_plate_resolution"].split("x")[0]) if "x" in r["best_plate_resolution"] else 0,
                r["best_plate_sharpness"]
            ), reverse=True)

            for idx, r in enumerate(results, start=1):
                r["rank"] = idx

            assessment_summary = {
                "assessment_id": f"diagnostic_{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_cameras_diagnosed": len(results),
                "confirmed_anpr_capable_count": sum(1 for r in results if r["classification"] == "CONFIRMED_ANPR_CAPABLE"),
                "potential_anpr_capable_count": sum(1 for r in results if r["classification"] == "POTENTIAL_ANPR_CAPABLE"),
                "vehicle_analytics_only_count": sum(1 for r in results if r["classification"] == "VEHICLE_ANALYTICS_ONLY"),
                "top_ranked_camera": results[0]["camera_id"] if results else None,
                "results": results
            }

            return assessment_summary

        finally:
            self.is_running = False

# Global singleton instance
anpr_diagnostic_service = ANPRDiagnosticService()
