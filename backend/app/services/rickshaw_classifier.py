import cv2
import numpy as np
import logging
from typing import Tuple, Dict, Any
from app.config import get_settings

logger = logging.getLogger(__name__)

class ConfidenceRickshawClassifier:
    """
    PHASE 11: Confidence-Based Secondary Vehicle Classifier for Auto-Rickshaws.
    Combines primary YOLO predictions, geometric aspect-ratio bounds, area ratios,
    and visual feature/color profiles to compute a validated probability score.
    
    Protects truck/car count integrity by outputting 'auto_rickshaw' ONLY when
    combined confidence >= AUTO_RICKSHAW_CONFIDENCE_THRESHOLD (0.75).
    """
    def __init__(self):
        self.settings = get_settings()
        self.min_confidence_threshold = self.settings.AUTO_RICKSHAW_CONFIDENCE_THRESHOLD

    def classify_vehicle_crop(
        self,
        frame: np.ndarray,
        bbox: list,
        primary_class: str,
        primary_conf: float
    ) -> Tuple[str, float]:
        """
        Evaluate vehicle crop ROI and return validated vehicle_type and confidence.
        """
        if frame is None or len(bbox) < 4:
            return primary_class, primary_conf

        fh, fw = frame.shape[:2]
        x1, y1, x2, y2 = bbox
        
        # Clamp coordinates
        x1, y1 = max(0, int(x1)), max(0, int(y1))
        x2, y2 = min(fw, int(x2)), min(fh, int(y2))

        bw = x2 - x1
        bh = y2 - y1

        if bw < 10 or bh < 10:
            return primary_class, primary_conf

        crop = frame[y1:y2, x1:x2]
        crop_area = bw * bh
        frame_area = fw * fh
        area_ratio = crop_area / float(frame_area)
        aspect_ratio = bw / float(bh)

        # 1. Geometry Scoring for Auto-Rickshaws (Compact 3-wheeler profile: AR ~ 0.80 to 1.30)
        geom_score = 0.0
        if 0.75 <= aspect_ratio <= 1.35:
            geom_score = 0.50
        elif 0.65 <= aspect_ratio <= 1.50:
            geom_score = 0.30

        # 2. Color Profile Analysis (Yellow / CNG Green HSV Coverage)
        color_score = 0.0
        try:
            hsv = cv2.cvtColor(crop, cv2.COLOR_BGR2HSV)
            # Yellow HSV range (typical top/body of Indian auto-rickshaws)
            yellow_mask = cv2.inRange(hsv, np.array([12, 70, 70]), np.array([38, 255, 255]))
            # CNG Green/Yellow range
            cng_mask = cv2.inRange(hsv, np.array([35, 60, 60]), np.array([75, 255, 255]))
            
            combined_mask = cv2.bitwise_or(yellow_mask, cng_mask)
            color_coverage = float(cv2.countNonZero(combined_mask)) / float(crop_area)
            color_score = min(0.50, color_coverage * 2.5)
        except Exception:
            color_score = 0.0

        # 3. Compute Combined Rickshaw Probability Score
        p_rickshaw = geom_score + color_score

        # 4. Classification Decision Logic
        # Case A: High Confidence Auto-Rickshaw match (>= 0.75)
        if p_rickshaw >= self.min_confidence_threshold:
            logger.debug(f"Reclassified {primary_class} -> AUTO_RICKSHAW (Score: {p_rickshaw:.2f}, AR: {aspect_ratio:.2f})")
            return "auto_rickshaw", round(p_rickshaw, 2)

        # Case B: Primary prediction was TRUCK, but geometry is compact and NOT long truck (AR < 1.35)
        # Avoid corrupting TRUCK metric -> flag as ambiguous if unresolvable
        if primary_class == "truck" and aspect_ratio <= 1.25 and area_ratio < 0.12:
            return "ambiguous", round(primary_conf, 2)

        # Case C: Retain original YOLO prediction
        return primary_class, primary_conf

# Singleton instance
rickshaw_classifier = ConfidenceRickshawClassifier()
