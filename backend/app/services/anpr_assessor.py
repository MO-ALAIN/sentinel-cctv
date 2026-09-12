import os
import time
import logging
import cv2
import numpy as np
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from app.config import get_settings
from app.services.catalogue import catalogue_service
from app.services.yolo_service import yolo_detector
from app.services.plate_detector import modular_plate_detector
from app.services.anpr_service import anpr_manager, MultiVariantOCRPreprocessor, IndianPlateValidator

logger = logging.getLogger(__name__)

os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"

class ANPRCameraAssessor:
    """
    Automated Multi-Camera Quality and ANPR Suitability Assessment Service.
    Evaluates reachability, vehicle presence, plate resolution, image sharpness,
    contrast, and OCR readability to rank cameras for license plate recognition.
    """
    def __init__(self):
        self.settings = get_settings()
        self.is_running: bool = False
        self.latest_assessment: Optional[Dict[str, Any]] = None

    def calculate_suitability_score(
        self,
        best_plate_w: int,
        best_plate_h: int,
        avg_sharpness: float,
        avg_contrast: float,
        best_det_conf: float,
        ocr_success_rate: float
    ) -> Dict[str, Any]:
        """
        Calculates ANPR Suitability Score (0 - 100) and classification based on objective metrics.
        - 30 pts: Plate Resolution
        - 25 pts: Image Sharpness
        - 15 pts: Contrast
        - 15 pts: Plate Detection Confidence
        - 15 pts: OCR Readability Evidence
        """
        # 1. Resolution Score (30 pts)
        w_pts = min(20.0, (best_plate_w / 80.0) * 20.0) if best_plate_w > 0 else 0.0
        h_pts = min(10.0, (best_plate_h / 25.0) * 10.0) if best_plate_h > 0 else 0.0
        resolution_score = round(w_pts + h_pts, 1)

        # 2. Sharpness Score (25 pts)
        sharpness_score = round(min(25.0, (avg_sharpness / 120.0) * 25.0), 1)

        # 3. Contrast Score (15 pts)
        contrast_score = round(min(15.0, (avg_contrast / 35.0) * 15.0), 1)

        # 4. Plate Detection Confidence Score (15 pts)
        plate_det_score = round(min(15.0, best_det_conf * 15.0), 1)

        # 5. OCR Readability Score (15 pts)
        ocr_score = round(min(15.0, ocr_success_rate * 15.0), 1)

        total_score = round(resolution_score + sharpness_score + contrast_score + plate_det_score + ocr_score, 1)

        if total_score >= 90:
            classification = "EXCELLENT"
        elif total_score >= 75:
            classification = "GOOD"
        elif total_score >= 55:
            classification = "MODERATE"
        elif total_score >= 30:
            classification = "POOR"
        else:
            classification = "UNSUITABLE"

        return {
            "total_score": total_score,
            "classification": classification,
            "breakdown": {
                "resolution_score": resolution_score,
                "sharpness_score": sharpness_score,
                "contrast_score": contrast_score,
                "plate_detection_score": plate_det_score,
                "ocr_readability_score": ocr_score
            }
        }

    async def assess_single_camera(
        self,
        cam_info: Dict[str, Any],
        duration_seconds: int = 20,
        sample_interval: int = 5
    ) -> Dict[str, Any]:
        """
        Assess connectivity, frame sampling, vehicle detection, plate ROI resolution,
        sharpness, contrast, and OCR readability for a single camera feed.
        """
        cam_id = cam_info["id"]
        cam_name = cam_info["name"]
        rtsp_url = cam_info["rtsp_url"]

        logger.info(f"Assessing camera {cam_id} ({cam_name}) via RTSP...")

        conn_start = time.time()
        cap = cv2.VideoCapture(rtsp_url, cv2.CAP_FFMPEG)
        
        # Connection Timeout / Fail Check
        if not cap.isOpened():
            logger.warning(f"Camera {cam_id} connection FAILED or OFFLINE.")
            return {
                "camera_id": cam_id,
                "camera_name": cam_name,
                "connection_status": "OFFLINE",
                "frames_processed": 0,
                "vehicles_detected": 0,
                "plate_candidates": 0,
                "best_plate_width": 0,
                "best_plate_height": 0,
                "average_sharpness": 0.0,
                "average_contrast": 0.0,
                "ocr_attempts": 0,
                "ocr_successes": 0,
                "anpr_score": 0.0,
                "classification": "UNSUITABLE",
                "score_breakdown": {},
                "debug_image": None,
                "timestamp": datetime.now(timezone.utc).isoformat()
            }

        frames_processed = 0
        yolo_runs = 0
        vehicles_detected = 0
        plate_candidates_count = 0

        plate_widths = []
        plate_heights = []
        sharpness_list = []
        contrast_list = []
        det_conf_list = []

        ocr_attempts = 0
        ocr_successes = 0

        annotated_sample_frame = None

        start_time = time.time()
        while (time.time() - start_time) < duration_seconds:
            ret, frame = cap.read()
            if not ret or frame is None:
                time.sleep(0.05)
                continue

            frames_processed += 1
            if frames_processed % sample_interval == 0:
                yolo_runs += 1
                
                # Step 4: CUDA YOLO Vehicle Detection + Tracking
                res = yolo_detector.track_vehicles(frame, cam_id)
                dets = res["detections"]
                annotated = res["annotated_frame"]
                vehicles_detected += len(dets)

                # Step 5 & 6: License Plate Candidate & Image Quality Analysis
                for d in dets:
                    bbox = d["bbox"]
                    # Run Modular Plate Detector on vehicle ROI
                    cands = modular_plate_detector.detect_plates(frame, vehicle_bbox=bbox)
                    if cands:
                        plate_candidates_count += len(cands)
                        top_cand = cands[0]
                        pcrop = top_cand["plate_crop"]
                        ph, pw = pcrop.shape[:2]

                        plate_widths.append(pw)
                        plate_heights.append(ph)
                        det_conf_list.append(top_cand["confidence"])

                        # Sharpness & Contrast Metrics
                        sharpness, contrast = MultiVariantOCRPreprocessor.compute_metrics(pcrop)
                        sharpness_list.append(sharpness)
                        contrast_list.append(contrast)

                        # Step 8: Limited OCR Validation on promising plate candidates (pw >= 35, ph >= 12)
                        if pw >= 35 and ph >= 12:
                            ocr_attempts += 1
                            variants = MultiVariantOCRPreprocessor.generate_variants(pcrop)
                            for var in variants:
                                try:
                                    out = anpr_manager.ocr_reader.readtext(var["image"])
                                    if out:
                                        raw_txt = " ".join([r[1] for r in out if len(r) >= 2])
                                        is_valid, _, _ = IndianPlateValidator.validate(raw_txt)
                                        if is_valid:
                                            ocr_successes += 1
                                            break
                                except Exception:
                                    pass

                if annotated_sample_frame is None and len(dets) > 0:
                    annotated_sample_frame = annotated.copy()

        cap.release()

        # Compute Aggregated Quality Metrics
        best_pw = max(plate_widths) if plate_widths else 0
        best_ph = max(plate_heights) if plate_heights else 0
        avg_sharp = float(np.mean(sharpness_list)) if sharpness_list else 0.0
        avg_contrast = float(np.mean(contrast_list)) if contrast_list else 0.0
        best_det_conf = max(det_conf_list) if det_conf_list else 0.0
        ocr_rate = (ocr_successes / float(ocr_attempts)) if ocr_attempts > 0 else 0.0

        # Calculate ANPR Suitability Score
        score_res = self.calculate_suitability_score(
            best_plate_w=best_pw,
            best_plate_h=best_ph,
            avg_sharpness=avg_sharp,
            avg_contrast=avg_contrast,
            best_det_conf=best_det_conf,
            ocr_success_rate=ocr_rate
        )

        from app.services.anpr_status_engine import anpr_status_engine
        anpr_status_info = anpr_status_engine.evaluate_camera_anpr_status(
            camera_id=cam_id,
            plate_candidates_count=plate_candidates_count,
            best_resolution_px=best_ph,
            best_quality_score=score_res["total_score"],
            ocr_attempts_count=ocr_attempts,
            confirmed_plates_count=ocr_successes
        )

        # Save Visual Debug Representative Image
        debug_img_path = None
        if annotated_sample_frame is not None or frame is not None:
            disp_frame = annotated_sample_frame if annotated_sample_frame is not None else frame.copy()
            # Overlay Banner
            banner_text = f"{cam_id.upper()} | STATUS: {anpr_status_info['anpr_status']} | SCORE: {score_res['total_score']}/100"
            cv2.rectangle(disp_frame, (0, 0), (750, 32), (0, 0, 0), -1)
            cv2.putText(disp_frame, banner_text, (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (0, 255, 255), 2, cv2.LINE_AA)

            scratch_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "scratch")
            os.makedirs(scratch_dir, exist_ok=True)
            debug_img_path = os.path.join(scratch_dir, f"anpr_assessment_{cam_id}.jpg")
            cv2.imwrite(debug_img_path, disp_frame)

        return {
            "camera_id": cam_id,
            "camera_name": cam_name,
            "connection_status": "ONLINE",
            "frames_processed": frames_processed,
            "vehicles_detected": vehicles_detected,
            "plate_candidates": plate_candidates_count,
            "best_plate_width": best_pw,
            "best_plate_height": best_ph,
            "average_sharpness": round(avg_sharp, 2),
            "average_contrast": round(avg_contrast, 2),
            "ocr_attempts": ocr_attempts,
            "ocr_successes": ocr_successes,
            "anpr_score": score_res["total_score"],
            "anpr_status": anpr_status_info["anpr_status"],
            "rationale": anpr_status_info["rationale"],
            "classification": score_res["classification"],
            "score_breakdown": score_res["breakdown"],
            "debug_image": debug_img_path,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }

    async def run_assessment_all_cameras(
        self,
        duration_per_camera: int = 20,
        target_camera_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Run multi-camera assessment across all configured Government CCTV feeds.
        Process sequentially to respect GPU VRAM & release RTSP streams after each camera.
        """
        if self.is_running:
            logger.warning("ANPR Assessment job is already running.")
            return {"status": "ALREADY_RUNNING", "message": "Assessment job in progress."}

        self.is_running = True
        logger.info("Starting Multi-Camera ANPR Capability Assessment Job...")

        try:
            catalogue = await catalogue_service.fetch_catalogue()
            if target_camera_id:
                catalogue = [c for c in catalogue if c["id"] == target_camera_id]

            results = []
            for cam_info in catalogue:
                res = await self.assess_single_camera(cam_info, duration_seconds=duration_per_camera)
                results.append(res)

            # Sort cameras by ANPR Suitability Score Descending
            results.sort(key=lambda item: item["anpr_score"], reverse=True)

            # Assign Ranks
            for idx, r in enumerate(results, start=1):
                r["rank"] = idx

            online_cams = [r for r in results if r["connection_status"] == "ONLINE"]
            offline_cams = [r for r in results if r["connection_status"] != "ONLINE"]
            suitable_cams = [r for r in results if r["anpr_score"] >= 55.0]

            recommended_cameras = [r["camera_id"] for r in suitable_cams]
            unsuitable_cameras = [r["camera_id"] for r in results if r["anpr_score"] < 55.0]

            assessment_summary = {
                "assessment_id": f"assessment_{int(time.time())}",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "total_cameras": len(catalogue),
                "online_cameras": len(online_cams),
                "offline_cameras": len(offline_cams),
                "anpr_suitable_cameras": len(suitable_cams),
                "recommended_cameras": recommended_cameras,
                "unsuitable_cameras": unsuitable_cameras,
                "top_ranked_camera": results[0]["camera_id"] if results else None,
                "results": results
            }

            self.latest_assessment = assessment_summary
            logger.info(f"Multi-Camera Assessment COMPLETE! Top Camera: {summary_top(results)}")
            return assessment_summary

        finally:
            self.is_running = False

def summary_top(results: List[Dict[str, Any]]) -> str:
    if not results:
        return "None"
    top = results[0]
    return f"{top['camera_id']} ({top['anpr_score']}/100 - {top['classification']})"

# Global singleton instance
anpr_assessor = ANPRCameraAssessor()
