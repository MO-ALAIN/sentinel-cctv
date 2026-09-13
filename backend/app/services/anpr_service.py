from app.paths import OCR_MODEL_DIR, MODEL_DIR
import os
import re
import time
import logging
import cv2
import numpy as np
try:
    import torch
except ImportError:
    torch = None
import threading
import uuid
import copy
from collections import OrderedDict, Counter
from app.paths import EVIDENCE_DIR
from datetime import datetime, timezone
from typing import Dict, List, Any, Optional, Tuple
from app.config import get_settings
from app.services.plate_detector import modular_plate_detector, HeuristicPlateDetector
from app.services.sighting_repository import sighting_repo

logger = logging.getLogger(__name__)

# Minimum Resolution Thresholds for Meaningful OCR
MIN_PLATE_WIDTH = 35
MIN_PLATE_HEIGHT = 12

# Indian License Plate Standard Patterns Regex
INDIAN_PLATE_PATTERNS = [
    r'^[A-Z]{2}[0-9]{2}[A-Z]{1,3}[0-9]{4}$',   # Standard e.g. GJ01AB1234, MH12DE5678, DL3CBA9999
    r'^[0-9]{2}BH[0-9]{4}[A-Z]{1,2}$',         # Bharat Series e.g. 22BH1234AA
    r'^[A-Z]{2}[0-9]{1,2}[A-Z]{1,3}[0-9]{1,4}$'  # Commercial / Vintage e.g. GJ1A1234
]

class IndianPlateValidator:
    """Normalizes and validates Indian vehicle registration plate formats with OCR confusion correction heuristics."""

    LETTER_CORRECTIONS = {'0': 'O', '1': 'I', '8': 'B', '5': 'S', '2': 'Z'}
    DIGIT_CORRECTIONS = {'O': '0', 'I': '1', 'Z': '2', 'S': '5', 'B': '8', 'G': '6', 'Q': '0'}

    @classmethod
    def clean_text(cls, raw_text: str) -> str:
        if not raw_text:
            return ""
        return re.sub(r'[^A-Za-z0-9]', '', raw_text).upper()

    @classmethod
    def apply_heuristics(cls, text: str) -> str:
        if len(text) < 7 or len(text) > 11:
            return text

        chars = list(text)
        # 1. State Code (Letters)
        for i in range(min(2, len(chars))):
            if chars[i] in cls.LETTER_CORRECTIONS:
                chars[i] = cls.LETTER_CORRECTIONS[chars[i]]

        # 2. District Code (Digits)
        for i in range(2, min(4, len(chars))):
            if chars[i] in cls.DIGIT_CORRECTIONS:
                chars[i] = cls.DIGIT_CORRECTIONS[chars[i]]

        # 3. Final 4 Digits
        start_last = max(4, len(chars) - 4)
        for i in range(start_last, len(chars)):
            if chars[i] in cls.DIGIT_CORRECTIONS:
                chars[i] = cls.DIGIT_CORRECTIONS[chars[i]]

        return "".join(chars)

    @classmethod
    def validate(cls, text: str) -> Tuple[bool, str, float]:
        cleaned = cls.clean_text(text)
        if not cleaned or len(cleaned) < 5:
            return False, cleaned, 0.0

        for pattern in INDIAN_PLATE_PATTERNS:
            if re.match(pattern, cleaned):
                return True, cleaned, 1.0

        corrected = cls.apply_heuristics(cleaned)
        for pattern in INDIAN_PLATE_PATTERNS:
            if re.match(pattern, corrected):
                return True, corrected, 0.9

        if len(corrected) >= 6 and re.match(r'^[A-Z]{2}[0-9]{2}', corrected):
            return False, corrected, 0.65  # Partial text may be reviewed, never confirmed.

        return False, corrected, 0.20


def validate_plate_for_source(text, plate_format='INDIA'):
    # Do not turn an ambiguous OCR stroke into a different valid registration by
    # deleting it. Spaces and hyphens are separators; embedded pipes/slashes/dots
    # may be an unresolved character. Edge punctuation can still be discarded.
    if re.search(r'[A-Za-z0-9]\s*[^A-Za-z0-9\s-]+\s*[A-Za-z0-9]', text or ''):
        return False, IndianPlateValidator.clean_text(text), 0.0
    if plate_format == 'INDIA':
        return IndianPlateValidator.validate(text)
    cleaned = IndianPlateValidator.clean_text(text)
    # Deliberately limited car/trailer format. No fuzzy substitutions or watchlist hints.
    # Traficom: 2-3 letters and a number of up to 3 digits; special types excluded.
    valid = plate_format == 'FINLAND_STANDARD' and bool(re.fullmatch(r'[A-Z]{2,3}[1-9][0-9]{0,2}', cleaned))
    return valid, cleaned, 1.0 if valid else 0.0


class MultiVariantOCRPreprocessor:
    """
    Step 5 & 7: Multi-variant image upscaling and preprocessing pipeline.
    Tests Variant A (Lanczos), Variant B (CLAHE + Cubic), Variant C (Bilateral Denoise)
    to compare OCR evidence and select the clearest result.
    """
    @staticmethod
    def compute_metrics(crop: np.ndarray) -> Tuple[float, float]:
        if crop is None or crop.size == 0:
            return 0.0, 0.0
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY) if len(crop.shape) == 3 else crop
        sharpness = float(cv2.Laplacian(gray, cv2.CV_64F).var())
        contrast = float(np.std(gray))
        return sharpness, contrast

    @classmethod
    def generate_variants(cls, plate_crop: np.ndarray) -> List[Dict[str, Any]]:
        if plate_crop is None or plate_crop.size == 0:
            return []

        # Add 15px border padding around plate crop to prevent character edge clipping
        padded_crop = cv2.copyMakeBorder(plate_crop, 15, 15, 25, 25, cv2.BORDER_CONSTANT, value=[255, 255, 255])

        h, w = padded_crop.shape[:2]
        target_h = 96
        scale = target_h / float(h) if h > 0 else 1.0
        target_w = int(w * scale)

        gray = cv2.cvtColor(padded_crop, cv2.COLOR_BGR2GRAY) if len(padded_crop.shape) == 3 else padded_crop

        # Variant A: Original + Lanczos Upscaling
        var_a = cv2.resize(gray, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)

        # Variant B: CLAHE Contrast Enhancement + Cubic Upscaling
        clahe = cv2.createCLAHE(clipLimit=2.5, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        var_b = cv2.resize(enhanced, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        # Variant C: Bilateral Denoising + Upscaling
        denoised = cv2.bilateralFilter(gray, 9, 75, 75)
        var_c = cv2.resize(denoised, (target_w, target_h), interpolation=cv2.INTER_CUBIC)

        return [
            {"variant_id": "A_LANCZOS", "image": var_a},
            {"variant_id": "B_CLAHE_CUBIC", "image": var_b},
            {"variant_id": "C_DENOISED", "image": var_c}
        ]


class ANPRManager:
    """
    Singleton ANPR Manager orchestrating Primary+Fallback Plate Detectors, Minimum Resolution Check,
    Multi-Variant Preprocessing, EasyOCR Engine, Format Validation, Diagnostic Rejection Classification,
    and Temporal Consensus Voting.
    """
    def __init__(self):
        self.settings = get_settings()
        self.ocr_reader = None
        self.gpu_available = False
        self.ocr_engine = "UNAVAILABLE"
        self.ocr_initialization_error = None

        # Multi-frame candidate buffers per vehicle track: Dict[track_key, List[CandidateFrame]]
        self._candidate_buffers: Dict[str, List[Dict[str, Any]]] = {}

        # Persistent ANPR Records: Dict[track_key, Dict[str, Any]]
        self._anpr_records: Dict[str, Dict[str, Any]] = {}

        # Track keys already written to the durable sighting store (one sighting per
        # camera appearance â€” recorded once when the plate first becomes confirmed).
        self._persisted_tracks: set = set()
        self._live_tracks = OrderedDict()
        self.evicted_tracks = 0
        self.detector_runs_count = 0

        # Telemetry & Diagnostic Rejection Counters
        self.total_vehicles_analysed: int = 0
        self.total_plates_detected: int = 0
        self.total_readable_plates: int = 0
        self.total_unreadable_plates: int = 0
        self.total_det_latency_ms: float = 0.0
        self.total_ocr_latency_ms: float = 0.0
        self.ocr_runs_count: int = 0

        self.rejection_breakdown: Dict[str, int] = {
            "TOO_SMALL": 0,
            "MOTION_BLUR": 0,
            "LOW_CONTRAST": 0,
            "INVALID_FORMAT": 0,
            "OCR_FAILED": 0
        }

        self._ocr_lock = threading.RLock()
        self._initialize_ocr()

    def _initialize_ocr(self):
        logger.info("Initializing EasyOCR Engine for Phase 7.5 ANPR...")
        self.gpu_available = torch is not None and torch.cuda.is_available() and self.settings.ANPR_USE_GPU
        if torch is None or not self.settings.AI_ENABLED:
            return
        if self.settings.ANPR_OCR_ENGINE == 'plate_onnx':
            try:
                from app.services.plate_ocr import PlateOCR
                self.ocr_reader = PlateOCR(MODEL_DIR / 'plate_ocr', self.settings.PLATE_OCR_MIN_CHAR_CONFIDENCE)
                self.ocr_engine = 'PLATE_ONNX_CCT_S_V2'
                self.gpu_available = False
                return
            except Exception as error:
                self.ocr_initialization_error = type(error).__name__ + ': optional plate OCR unavailable; using EasyOCR fallback'
                logger.warning(self.ocr_initialization_error)
        try:
            import easyocr
            self.ocr_reader = easyocr.Reader(['en'], gpu=self.gpu_available, verbose=False, model_storage_directory=str(OCR_MODEL_DIR), download_enabled=self.settings.ALLOW_MODEL_DOWNLOAD)
            self.ocr_engine = "EasyOCR"
            logger.info(f"EasyOCR Reader initialized (GPU Acceleration: {self.gpu_available}).")
        except Exception as e:
            logger.error(f"Failed to initialize EasyOCR Reader: {e}")
            self.ocr_reader = None

    def process_vehicle_crop(self, *args, **kwargs):
        with self._ocr_lock:
            # Callers must not hold mutable recognition state after this lock is released.
            return copy.deepcopy(self._process_vehicle_crop(*args, **kwargs))

    def _touch_track(self, key):
        self._live_tracks[key] = None
        self._live_tracks.move_to_end(key)
        while len(self._live_tracks) > self.settings.ANPR_MAX_CACHED_TRACKS:
            expired, _ = self._live_tracks.popitem(last=False)
            self._candidate_buffers.pop(expired, None)
            self._anpr_records.pop(expired, None)
            self._persisted_tracks.discard(expired)
            self.evicted_tracks += 1

    def _process_vehicle_crop(
        self,
        camera_id: str,
        track_id: Optional[int],
        vehicle_type: str,
        full_frame: np.ndarray,
        vehicle_bbox: List[int],
        timestamp: str,
        session_id: Optional[str] = None,
        media_offset_seconds: Optional[float] = None,
        timestamp_basis: str = 'PROCESSING_TIME',
    ) -> Optional[Dict[str, Any]]:
        """
        Full ANPR Pipeline: Runs Primary+Fallback Plate Detector, Minimum Resolution Check,
        Multi-Variant Preprocessing, EasyOCR, Format Validation, Rejection Diagnostics, and Temporal Consensus.
        """
        if full_frame is None or full_frame.size == 0 or track_id is None:
            return None

        plate_format = self.settings.ANPR_CAMERA_FORMATS.get(camera_id, 'INDIA')
        track_key = (camera_id, session_id or 'legacy', track_id)
        self._touch_track(track_key)
        if track_key in self._persisted_tracks:
            self._anpr_records[track_key]['last_seen'] = timestamp
            return self._anpr_records.get(track_key)
        det_start = time.time()

        # Step 2 & 3: Run Modular License Plate Detector (Primary Trained + Secondary Fallback with ROI)
        plate_candidates = modular_plate_detector.detect_plates(full_frame, vehicle_bbox=vehicle_bbox)
        det_latency = (time.time() - det_start) * 1000.0
        self.detector_runs_count += 1
        self.total_det_latency_ms += det_latency

        if not plate_candidates:
            return None

        best_cand = plate_candidates[0]
        plate_crop = best_cand["plate_crop"]
        det_conf = best_cand["confidence"]
        det_method = best_cand["detection_method"]
        abs_plate_bbox = best_cand.get("abs_bbox", best_cand["bbox"])
        if not np.isfinite(det_conf) or not 0 <= det_conf <= 1:
            return None

        ph, pw = plate_crop.shape[:2]

        # Step 4: Minimum Resolution Check
        if pw < MIN_PLATE_WIDTH or ph < MIN_PLATE_HEIGHT:
            self.rejection_breakdown["TOO_SMALL"] += 1
            self.total_unreadable_plates += 1
            previous = self._anpr_records.get(track_key)
            if previous is not None:
                previous.update(last_seen=timestamp, latest_rejection_reason="TOO_SMALL")
                return previous
            record = {
                "camera_id": camera_id,
                "track_id": track_id,
                "vehicle_type": vehicle_type,
                "plate_number": "TOO_SMALL",
                "status": "TOO_SMALL",
                "rejection_reason": "TOO_SMALL",
                "plate_width": pw,
                "plate_height": ph,
                "detection_method": det_method,
                "plate_confidence": 0.0,
                "detector_confidence": det_conf,
                "ocr_confidence": 0.0,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "best_frame_timestamp": timestamp,
                "abs_plate_bbox": abs_plate_bbox,
                "consensus_votes": {}
            }
            self._anpr_records[track_key] = record
            return record

        # Step 6: Quality Metrics Calculation
        sharpness, contrast = MultiVariantOCRPreprocessor.compute_metrics(plate_crop)

        if sharpness < 20.0:
            rejection = "MOTION_BLUR"
        elif contrast < 12.0:
            rejection = "LOW_CONTRAST"
        else:
            rejection = None

        # Poor source detail must not count as an independent confirmation vote,
        # even when OCR confidently hallucinates a valid-looking registration.
        if rejection:
            self.rejection_breakdown[rejection] += 1
            self.total_unreadable_plates += 1
            record = self._anpr_records.setdefault(track_key, {
                "camera_id": camera_id, "track_id": track_id, "vehicle_type": vehicle_type,
                "plate_number": "UNREADABLE", "status": "UNREADABLE",
                "rejection_reason": rejection, "plate_width": pw, "plate_height": ph,
                "detection_method": det_method, "plate_confidence": 0.0,
                "detector_confidence": det_conf, "ocr_confidence": 0.0,
                "first_seen": timestamp, "best_frame_timestamp": timestamp,
                "abs_plate_bbox": abs_plate_bbox, "consensus_votes": {}, "voted_timestamps": set(),
            })
            record.update(last_seen=timestamp, latest_rejection_reason=rejection)
            return record

        # Step 2: Multi-Frame Candidate Buffer
        if track_key not in self._candidate_buffers:
            self._candidate_buffers[track_key] = []
            self.total_vehicles_analysed += 1

        cand_entry = {
            "plate_crop": plate_crop,
            "abs_plate_bbox": abs_plate_bbox,
            "det_method": det_method,
            "det_confidence": det_conf,
            "sharpness": sharpness,
            "contrast": contrast,
            "plate_width": pw,
            "plate_height": ph,
            "timestamp": timestamp
        }

        buf = self._candidate_buffers[track_key]
        # Numpy plate crops can be views into a full HD frame. Historical quality
        # metadata needs no pixels; keeping the view would retain the entire frame.
        buf.append({k: v for k, v in cand_entry.items() if k != 'plate_crop'})
        if len(buf) > self.settings.ANPR_MAX_CANDIDATES_PER_TRACK:
            buf.pop(0)

        # Select Best Candidate based on composite quality
        top_cand = cand_entry  # One independent source frame per consensus vote.

        # Step 5 & 7: Multi-Variant OCR Ensemble
        if self.ocr_reader is None:
            return None

        ocr_start = time.time()
        variants = ([{"variant_id":"PLATE_ORIGINAL", "image":top_cand["plate_crop"]}]
                    if self.ocr_engine == "PLATE_ONNX_CCT_S_V2"
                    else MultiVariantOCRPreprocessor.generate_variants(top_cand["plate_crop"]))

        best_variant_result = None
        highest_composite_score = -1.0

        for var in variants:
            try:
                ocr_out = self.ocr_reader.readtext(var["image"])
            except Exception as e:
                logger.error(f"OCR error on variant {var['variant_id']}: {e}")
                ocr_out = []

            raw_txt = ""
            ocr_conf = 0.0
            if ocr_out:
                txt_parts = [r[1] for r in ocr_out if len(r) >= 2]
                conf_parts = [r[2] for r in ocr_out if len(r) >= 3]
                scores = np.asarray(conf_parts, dtype=float)
                # Every text segment needs valid confidence. A high-confidence
                # prefix must not hide an uncertain registration suffix.
                if len(conf_parts) == len(txt_parts) and scores.size and np.isfinite(scores).all() and ((scores >= 0) & (scores <= 1)).all():
                    raw_txt = " ".join(txt_parts)
                    ocr_conf = float(scores.min())

            is_valid, final_plate, val_score = validate_plate_for_source(raw_txt, plate_format)
            detector_score = top_cand["det_confidence"]
            composite_score = ocr_conf * detector_score * val_score if np.isfinite(detector_score) and 0 <= detector_score <= 1 else 0.0

            if composite_score > highest_composite_score:
                highest_composite_score = composite_score
                best_variant_result = {
                    "raw_text": raw_txt,
                    "final_plate": final_plate,
                    "is_valid": is_valid,
                    "ocr_conf": ocr_conf,
                    "val_score": val_score,
                    "variant_id": var["variant_id"],
                    "composite_score": composite_score
                }

        ocr_latency = (time.time() - ocr_start) * 1000.0
        self.total_ocr_latency_ms += ocr_latency
        self.ocr_runs_count += 1
        self.total_plates_detected += 1

        if not best_variant_result or not best_variant_result["raw_text"]:
            rejection_reason = rejection if rejection else "OCR_FAILED"
            self.rejection_breakdown[rejection_reason] += 1
            self.total_unreadable_plates += 1
            status = "UNREADABLE"
            final_plate = "UNREADABLE"
        elif best_variant_result["is_valid"] and best_variant_result["composite_score"] >= self.settings.ANPR_MIN_CONFIDENCE:
            status = "CONFIRMED"
            rejection_reason = None
            final_plate = best_variant_result["final_plate"]
            self.total_readable_plates += 1
        elif len(best_variant_result["final_plate"]) >= 5 and best_variant_result["composite_score"] >= 0.30:
            status = "LOW_CONFIDENCE"
            rejection_reason = None
            final_plate = best_variant_result["final_plate"]
            self.total_readable_plates += 1
        else:
            rejection_reason = rejection if rejection else "INVALID_FORMAT"
            self.rejection_breakdown[rejection_reason] += 1
            self.total_unreadable_plates += 1
            status = "UNREADABLE"
            final_plate = "UNREADABLE"

        # Temporal Consensus Record Update
        if track_key not in self._anpr_records:
            self._anpr_records[track_key] = {
                "camera_id": camera_id,
                "track_id": track_id,
                "vehicle_type": vehicle_type,
                "plate_number": final_plate,
                "status": "LOW_CONFIDENCE" if status == "CONFIRMED" else status,
                "rejection_reason": rejection_reason,
                "plate_width": pw,
                "plate_height": ph,
                "detection_method": top_cand["det_method"],
                "plate_confidence": round(highest_composite_score, 3),
                "detector_confidence": round(top_cand["det_confidence"], 3),
                "ocr_confidence": round(best_variant_result["ocr_conf"], 3) if best_variant_result else 0.0,
                "first_seen": timestamp,
                "last_seen": timestamp,
                "best_frame_timestamp": top_cand["timestamp"],
                "abs_plate_bbox": top_cand["abs_plate_bbox"],
                "consensus_votes": {},
                "voted_timestamps": set()
            }
        rec = self._anpr_records[track_key]
        rec['last_seen'] = timestamp
        if status == 'CONFIRMED' and timestamp not in rec.get('voted_timestamps', set()):
            qualified = rec.setdefault('qualifying_votes', [])
            qualified.append({'plate': final_plate, 'timestamp': timestamp, 'score': highest_composite_score})
            del qualified[:-self.settings.ANPR_MAX_CANDIDATES_PER_TRACK]
            votes = Counter(v['plate'] for v in qualified)
            winner, count = votes.most_common(1)[0]
            # Tied conflicting strings remain provisional. The confidence belongs
            # to this registration, never to a stronger read of a different plate.
            unique_winner = sum(n == count for n in votes.values()) == 1
            rec.update(consensus_votes=dict(votes), voted_timestamps={v['timestamp'] for v in qualified},
                plate_number=winner, status='CONFIRMED' if count >= 2 and unique_winner and winner == final_plate else 'LOW_CONFIDENCE',
                rejection_reason=None)
            if winner == final_plate:
                rec.update(plate_confidence=round(min(v['score'] for v in qualified if v['plate'] == winner), 3),
                    detector_confidence=round(det_conf, 3), ocr_confidence=round(best_variant_result['ocr_conf'], 3),
                    abs_plate_bbox=top_cand['abs_plate_bbox'], best_frame_timestamp=timestamp,
                    plate_width=pw, plate_height=ph, detection_method=det_method)

        # --- Durable sighting persistence (enables cross-camera trace + watchlist alerts) ---
        self._anpr_records[track_key]["plate_format"] = plate_format

        # Write only after independent qualified frames confirm the same plate.
        rec = self._anpr_records[track_key]
        if status == "CONFIRMED" and rec["status"] == "CONFIRMED" and final_plate == rec["plate_number"] and track_key not in self._persisted_tracks:
            try:
                crop_path = self._save_sighting_crop(
                    camera_id, track_id, rec["plate_number"], top_cand.get("plate_crop")
                )
                sighting_repo.record_sighting(
                    plate_number=rec["plate_number"],
                    camera_id=camera_id,
                    track_id=track_id,
                    vehicle_type=vehicle_type,
                    status=rec["status"],
                    confidence=rec.get("plate_confidence"),
                    sighted_at=timestamp,
                    crop_path=crop_path, session_id=session_id,
                    media_offset_seconds=media_offset_seconds,
                    timestamp_basis=timestamp_basis,
                )
                self._persisted_tracks.add(track_key)
                self._candidate_buffers.pop(track_key, None)
            except Exception as e:
                logger.error(f"Failed to persist sighting for {track_key}: {e}")

        return self._anpr_records[track_key]

    def _save_sighting_crop(
        self, camera_id: str, track_id: Optional[int], plate_number: str, plate_crop
    ) -> Optional[str]:
        """Save the plate crop as evidence for a sighting. Returns the path or None."""
        if plate_crop is None or getattr(plate_crop, "size", 0) == 0:
            return None
        try:
            out_dir = str(EVIDENCE_DIR)
            os.makedirs(out_dir, exist_ok=True)
            safe_plate = "".join(c for c in (plate_number or "UNK") if c.isalnum()) or "UNK"
            path = os.path.join(out_dir, f"{uuid.uuid4().hex}.jpg")
            if not cv2.imwrite(path, plate_crop):
                return None
            return os.path.basename(path)
        except Exception:
            return None

    def reset_camera(self, camera_id):
        with self._ocr_lock:
            for store in (self._candidate_buffers, self._anpr_records, self._live_tracks):
                for key in list(store):
                    if key[0] == camera_id:
                        store.pop(key, None)
            self._persisted_tracks = {k for k in self._persisted_tracks if k[0] != camera_id}

    def get_records(
        self,
        camera_id: Optional[str] = None,
        track_id: Optional[int] = None,
        plate_number: Optional[str] = None,
        status: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        with self._ocr_lock:
            results = copy.deepcopy(list(self._anpr_records.values()))

        if camera_id:
            results = [r for r in results if r["camera_id"] == camera_id]
        if track_id is not None:
            results = [r for r in results if r["track_id"] == track_id]
        if plate_number:
            query_clean = IndianPlateValidator.clean_text(plate_number)
            results = [r for r in results if query_clean in IndianPlateValidator.clean_text(r["plate_number"])]
        if status:
            results = [r for r in results if r["status"].upper() == status.upper()]

        results.sort(key=lambda r: r["last_seen"], reverse=True)
        return results[:limit]

    def search_plate(self, query: str) -> List[Dict[str, Any]]:
        return self.get_records(plate_number=query)

    def get_telemetry(self) -> Dict[str, Any]:
        avg_det = (self.total_det_latency_ms / self.detector_runs_count) if self.detector_runs_count > 0 else 0.0
        avg_ocr = (self.total_ocr_latency_ms / self.ocr_runs_count) if self.ocr_runs_count > 0 else 0.0
        return {
            "ocr_engine": self.ocr_engine,
            "requested_ocr_engine": self.settings.ANPR_OCR_ENGINE,
            "ocr_initialization_error": self.ocr_initialization_error,
            "default_plate_format": "INDIA",
            "camera_plate_formats": self.settings.ANPR_CAMERA_FORMATS,
            "plate_detector": "TRAINED_BASELINE" if modular_plate_detector.trained_detector.model is not None else "CV_HEURISTIC",
            "trained_plate_detector_ready": modular_plate_detector.trained_detector.model is not None,
            "ready": self.ocr_reader is not None,
            "gpu_acceleration": self.gpu_available,
            "device": "cuda:0" if self.gpu_available else "cpu",
            "total_vehicles_analysed": self.total_vehicles_analysed,
            "total_plates_detected": self.total_plates_detected,
            "readable_plates": self.total_readable_plates,
            "unreadable_plates": self.total_unreadable_plates,
            "rejection_breakdown": self.rejection_breakdown,
            "avg_plate_detection_latency_ms": round(avg_det, 2),
            "avg_ocr_latency_ms": round(avg_ocr, 2),
            "max_candidates_per_track": self.settings.ANPR_MAX_CANDIDATES_PER_TRACK,
            "cached_tracks": len(self._live_tracks),
            "max_cached_tracks": self.settings.ANPR_MAX_CACHED_TRACKS,
            "evicted_tracks": self.evicted_tracks,
            "plate_detector_runs": self.detector_runs_count,
        }

# Global singleton instance
anpr_manager = ANPRManager()
