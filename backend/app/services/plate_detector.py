import os
import time
import logging
import cv2
import numpy as np
try:
    import torch
    from ultralytics import YOLO
except ImportError:
    torch = None
    YOLO = None
from typing import List, Dict, Any, Optional, Tuple
from app.config import get_settings
from app.paths import MODEL_DIR

logger = logging.getLogger(__name__)

class HeuristicPlateDetector:
    """
    FALLBACK / SECONDARY DETECTOR: Uncalibrated CV candidate locator
    Uses Morphological Top-Hat, Sobel-X Vertical Edges, Contrast Enhancement, and Aspect-Ratio Filtering.
    """
    @classmethod
    def detect(cls, image: np.ndarray) -> List[Dict[str, Any]]:
        if image is None or image.size == 0:
            return []

        ih, iw = image.shape[:2]
        if ih < 25 or iw < 25:
            return []

        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image

        # Morphological Top-Hat Filter
        rect_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (13, 5))
        top_hat = cv2.morphologyEx(gray, cv2.MORPH_TOPHAT, rect_kernel)

        # Sobel-x Vertical Edges
        sobel_x = cv2.Sobel(top_hat, cv2.CV_32F, 1, 0, ksize=-1)
        sobel_x = np.absolute(sobel_x)
        min_val, max_val = np.min(sobel_x), np.max(sobel_x)
        if max_val > min_val:
            sobel_x = (255 * ((sobel_x - min_val) / (max_val - min_val))).astype("uint8")
        else:
            sobel_x = sobel_x.astype("uint8")

        blurred = cv2.GaussianBlur(sobel_x, (5, 5), 0)
        close_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (21, 7))
        closed = cv2.morphologyEx(blurred, cv2.MORPH_CLOSE, close_kernel)
        thresh = cv2.threshold(closed, 0, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)[1]

        contours, _ = cv2.findContours(thresh.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []

        for c in contours:
            x, y, w, h = cv2.boundingRect(c)
            if h == 0 or w == 0:
                continue

            aspect_ratio = float(w) / float(h)
            area = w * h

            if 2.0 <= aspect_ratio <= 6.0 and area > 350 and w >= 35 and h >= 10:
                pos_bias = 1.2 if (y + h / 2.0) > (ih * 0.4) else 0.8
                confidence = min(0.85, ((area / (iw * ih)) * 10.0 + (aspect_ratio / 6.0) * 0.3) * pos_bias)
                
                plate_crop = image[y:y+h, x:x+w]
                candidates.append({
                    "detection_method": "CV_HEURISTIC",
                    "bbox": [x, y, x + w, y + h],
                    "confidence": round(float(confidence), 3),
                    "plate_crop": plate_crop,
                    "aspect_ratio": round(aspect_ratio, 2),
                    "area": area
                })

        candidates.sort(key=lambda item: item["confidence"], reverse=True)
        return candidates[:3]


class TrainedPlateDetector:
    """
    PRIMARY DETECTOR: Native YOLO License Plate Detector
    Utilizes PyTorch YOLO model weights if available, or falls back to CV heuristic detector.
    """
    def __init__(self):
        self.settings = get_settings()
        self.model: Optional[YOLO] = None
        self.device: str = "cuda:0" if torch is not None and torch.cuda.is_available() else "cpu"
        self.model_path = str(MODEL_DIR / "license_plate_detector.pt")
        self._initialize_model()

    def _initialize_model(self):
        if YOLO is not None and self.settings.AI_ENABLED and os.path.exists(self.model_path):
            try:
                logger.info(f"Loading local Trained License Plate Detector weights from {self.model_path}...")
                self.model = YOLO(self.model_path)
                logger.info(f"Trained License Plate Detector loaded successfully on {self.device}!")
            except Exception as e:
                logger.warning(f"Could not load Trained Plate Detector model: {e}")
                self.model = None
        else:
            logger.info("Local trained license plate weights file not found. System using CV Heuristic Detector + EasyOCR OCR Ensemble.")
            self.model = None

    def detect(self, image: np.ndarray, conf_thresh: float = 0.25) -> List[Dict[str, Any]]:
        if self.model is None or image is None or image.size == 0:
            return []

        ih, iw = image.shape[:2]
        if ih < 25 or iw < 25:
            return []

        try:
            results = self.model.predict(
                source=image,
                device=self.device,
                conf=conf_thresh,
                verbose=False
            )
        except Exception as ex:
            logger.error(f"Error running Trained Plate Detector: {ex}")
            return []

        candidates = []
        if results and len(results) > 0:
            boxes = results[0].boxes
            for box in boxes:
                confidence = float(box.conf[0].item())
                xyxy = box.xyxy[0].cpu().numpy().tolist()
                x1, y1, x2, y2 = [int(v) for v in xyxy]
                
                x1, y1 = max(0, x1), max(0, y1)
                x2, y2 = min(iw, x2), min(ih, y2)
                w, h = x2 - x1, y2 - y1

                if w >= 15 and h >= 6:
                    plate_crop = image[y1:y2, x1:x2]
                    candidates.append({
                        "detection_method": "TRAINED_MODEL",
                        "bbox": [x1, y1, x2, y2],
                        "confidence": round(confidence, 3),
                        "plate_crop": plate_crop,
                        "aspect_ratio": round(w / float(h), 2) if h > 0 else 0.0,
                        "area": w * h
                    })

        candidates.sort(key=lambda item: item["confidence"], reverse=True)
        return candidates


def plate_belongs_to_vehicle(plate_bbox, vehicle_bbox) -> bool:
    """Require the plate center and most of its area to lie on the tracked vehicle.

    Padding helps detection, but a neighboring car's plate must not become this
    vehicle's identity. This conservative geometric check does not resolve occlusion.
    """
    px1, py1, px2, py2 = plate_bbox
    vx1, vy1, vx2, vy2 = vehicle_bbox
    area = (px2 - px1) * (py2 - py1)
    if px2 <= px1 or py2 <= py1 or vx2 <= vx1 or vy2 <= vy1:
        return False
    center_x, center_y = (px1 + px2) / 2, (py1 + py2) / 2
    overlap = max(0, min(px2, vx2) - max(px1, vx1)) * max(0, min(py2, vy2) - max(py1, vy1))
    return vx1 <= center_x <= vx2 and vy1 <= center_y <= vy2 and overlap / area >= 0.8


class ModularPlateDetector:
    """
    Orchestrates Primary Trained Plate Detector and Secondary CV Heuristic Detector
    Supports configurable ROI strategies: 'vehicle_roi', 'full_frame', 'hybrid'.
    """
    def __init__(self):
        self.trained_detector = TrainedPlateDetector()
        self.mode: str = "vehicle_roi"  # vehicle_roi, full_frame, hybrid

    def detect_plates(
        self,
        full_frame: np.ndarray,
        vehicle_bbox: Optional[List[int]] = None,
        padding_pct: float = 0.10
    ) -> List[Dict[str, Any]]:
        if full_frame is None or full_frame.size == 0:
            return []

        fh, fw = full_frame.shape[:2]
        candidates = []

        # Step 3: Vehicle ROI Strategy
        if vehicle_bbox and (self.mode == "vehicle_roi" or self.mode == "hybrid"):
            vx1, vy1, vx2, vy2 = vehicle_bbox
            vw, vh = vx2 - vx1, vy2 - vy1

            if vw >= 25 and vh >= 25:
                pad_w = int(vw * padding_pct)
                pad_h = int(vh * padding_pct)
                
                crop_x1 = max(0, vx1 - pad_w)
                crop_y1 = max(0, vy1 - pad_h)
                crop_x2 = min(fw, vx2 + pad_w)
                crop_y2 = min(fh, vy2 + pad_h)

                vehicle_roi = full_frame[crop_y1:crop_y2, crop_x1:crop_x2]

                # 1. Try Primary Trained Plate Detector on vehicle ROI if available
                roi_candidates = self.trained_detector.detect(vehicle_roi)

                # 2. Try Secondary Fallback CV Heuristic Detector
                if not roi_candidates:
                    roi_candidates = HeuristicPlateDetector.detect(vehicle_roi)

                for cand in roi_candidates:
                    bx1, by1, bx2, by2 = cand["bbox"]
                    cand["abs_bbox"] = [
                        crop_x1 + bx1,
                        crop_y1 + by1,
                        crop_x1 + bx2,
                        crop_y1 + by2
                    ]
                    if plate_belongs_to_vehicle(cand["abs_bbox"], vehicle_bbox):
                        candidates.append(cand)

        # Step 3 Fallback / Hybrid Mode: Try full_frame detection
        if not candidates and (self.mode == "full_frame" or self.mode == "hybrid"):
            ff_candidates = self.trained_detector.detect(full_frame)
            if not ff_candidates:
                ff_candidates = HeuristicPlateDetector.detect(full_frame)

            for cand in ff_candidates:
                cand["abs_bbox"] = cand["bbox"]
                if vehicle_bbox is None or plate_belongs_to_vehicle(cand["abs_bbox"], vehicle_bbox):
                    candidates.append(cand)

        candidates.sort(key=lambda c: c["confidence"], reverse=True)
        return candidates

# Global instance
modular_plate_detector = ModularPlateDetector()
