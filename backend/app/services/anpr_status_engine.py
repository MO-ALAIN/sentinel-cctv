import re
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Position-Aware Character Mappings for Indian Registration Numbers (GJ01AB1234)
DIGIT_TO_LETTER = {'0': 'O', '1': 'I', '5': 'S', '8': 'B'}
LETTER_TO_DIGIT = {'O': '0', 'I': '1', 'S': '5', 'B': '8', 'Z': '2', 'G': '6'}

def normalize_indian_plate_format(raw_ocr: str) -> Optional[str]:
    """
    Position-Aware Normalization for Indian License Plates (Format: GJ01AB1234 / GJ01A1234).
    Enforces format constraints:
    - Pos 0-1: State Letters (GJ, MH, DL, KA, MP, HR, RJ, UP)
    - Pos 2-3: District Digits (01-99)
    - Pos 4-5: Series Letters (A-ZZ)
    - Pos 6-9: Sequence Numbers (0001-9999)
    Never fabricates missing characters.
    """
    if not raw_ocr:
        return None

    clean = re.sub(r'[^A-Z0-9]', '', raw_ocr.upper().strip())
    if len(clean) not in [9, 10]:
        return None

    chars = list(clean)
    is_10_char = len(clean) == 10

    # Pos 0, 1: State Code (Letters)
    for i in range(2):
        if chars[i] in DIGIT_TO_LETTER:
            chars[i] = DIGIT_TO_LETTER[chars[i]]
        if not chars[i].isalpha():
            return None

    # Pos 2, 3: District Code (Digits)
    for i in range(2, 4):
        if chars[i] in LETTER_TO_DIGIT:
            chars[i] = LETTER_TO_DIGIT[chars[i]]
        if not chars[i].isdigit():
            return None

    # Pos 4 (and 5 if 10-char): Series Code (Letters)
    series_end = 6 if is_10_char else 5
    for i in range(4, series_end):
        if chars[i] in DIGIT_TO_LETTER:
            chars[i] = DIGIT_TO_LETTER[chars[i]]
        if not chars[i].isalpha():
            return None

    # Pos series_end to end: Sequence Number (Digits)
    for i in range(series_end, len(chars)):
        if chars[i] in LETTER_TO_DIGIT:
            chars[i] = LETTER_TO_DIGIT[chars[i]]
        if not chars[i].isdigit():
            return None

    normalized = "".join(chars)
    pattern = r'^[A-Z]{2}[0-9]{2}[A-Z]{1,2}[0-9]{4}$'
    if re.match(pattern, normalized):
        return normalized

    return None

class ANPRStatusEngine:
    """
    PHASE 11: Intelligent ANPR Camera Capability & Status Evaluator.
    Assigns strict empirical status:
    - ANPR_READY: Verified multi-frame OCR consensus confirmed + high quality score.
    - ANPR_POTENTIAL: Plate crops available & OCR attempted, but character consensus pending.
    - ANPR_LIMITED: Plate crops visible, but character resolution < 25px.
    - ANPR_UNSUITABLE: No usable plate candidates.
    """

    @staticmethod
    def evaluate_multi_frame_consensus(ocr_reads: List[str]) -> Tuple[bool, Optional[str], float]:
        """
        Evaluate multi-frame OCR consensus across a vehicle track history.
        Requires at least 2 identical normalized reads to confirm.
        """
        normalized_reads = []
        for raw in ocr_reads:
            norm = normalize_indian_plate_format(raw)
            if norm:
                normalized_reads.append(norm)

        if not normalized_reads:
            return False, None, 0.0

        # Frequency tally
        counts = {}
        for r in normalized_reads:
            counts[r] = counts.get(r, 0) + 1

        best_plate = max(counts, key=counts.get)
        best_count = counts[best_plate]

        # Multi-Frame Consensus Threshold (At least 2 consistent normalized reads)
        if best_count >= 2:
            confidence = min(0.98, 0.70 + (best_count * 0.10))
            return True, best_plate, round(confidence, 2)
        elif len(normalized_reads) == 1:
            return False, best_plate, 0.55
        else:
            return False, best_plate, 0.40

    @staticmethod
    def evaluate_camera_anpr_status(
        camera_id: str,
        plate_candidates_count: int,
        best_resolution_px: int,
        best_quality_score: float,
        ocr_attempts_count: int,
        confirmed_plates_count: int
    ) -> Dict[str, Any]:
        """
        Compute empirical ANPR capability status and detailed rationale.
        """
        # Strict Status Logic
        if confirmed_plates_count >= 1 and best_quality_score >= 70.0:
            status = "ANPR_READY"
            rationale = f"High plate resolution ({best_resolution_px}px) and multi-frame OCR consensus verified."
        elif ocr_attempts_count >= 1 and plate_candidates_count >= 1 and best_quality_score >= 50.0:
            status = "ANPR_POTENTIAL"
            rationale = "Plate regions detected and OCR attempted, but character-level multi-frame consensus is not yet confirmed."
        elif plate_candidates_count >= 1 or best_resolution_px >= 12:
            status = "ANPR_LIMITED"
            rationale = f"Vehicles visible, but character resolution ({best_resolution_px}px) is below threshold (< 25px) for reliable OCR."
        else:
            status = "ANPR_UNSUITABLE"
            rationale = "Camera geometry, angle, or resolution prevents plate character detection."

        return {
            "camera_id": camera_id,
            "anpr_status": status,
            "status": status,
            "plate_candidates": plate_candidates_count,
            "best_resolution_px": best_resolution_px,
            "best_quality_score": round(best_quality_score, 1),
            "ocr_attempts": ocr_attempts_count,
            "confirmed_plates": confirmed_plates_count,
            "rationale": rationale
        }

# Singleton instance
anpr_status_engine = ANPRStatusEngine()
