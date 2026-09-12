"""Optional pinned plate OCR, adapted to the existing readtext interface."""
import hashlib
from pathlib import Path
import cv2
import numpy as np

MODEL_HASH = "384bbbd2cea3ef54761d3df70822ef3a349ee1a112aeafddbe0e3ba06bc6e47b"
CONFIG_HASH = "0335c74a305173bb6f393efed0fde03cadeaa0b649ed8e19f431016d8232d0a6"


class PlateOCR:
    def __init__(self, directory: Path, minimum_char_confidence: float = 0.90):
        model = directory / 'cct_s_v2_global.onnx'
        config = directory / 'cct_s_v2_global_plate_config.yaml'
        for path, expected in ((model, MODEL_HASH), (config, CONFIG_HASH)):
            if not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                raise ValueError('Plate OCR model/config missing or checksum mismatch; run explicit setup')
        import onnxruntime as ort
        from fast_plate_ocr import LicensePlateRecognizer
        options = ort.SessionOptions()
        options.intra_op_num_threads = 2
        options.inter_op_num_threads = 1
        self.model = LicensePlateRecognizer(onnx_model_path=model, plate_config_path=config,
            device='cpu', sess_options=options)
        self.minimum_char_confidence = minimum_char_confidence

    def readtext(self, image):
        if image is None or image.size == 0:
            return []
        rgb = cv2.cvtColor(image, cv2.COLOR_GRAY2RGB if image.ndim == 2 else cv2.COLOR_BGR2RGB)
        prediction = self.model.run(rgb, return_confidence=True)[0]
        text = prediction.plate
        scores = np.asarray(prediction.char_probs, dtype=float) if prediction.char_probs is not None else np.array([])
        # The weakest character must clear the gate; an average can hide one wrong digit.
        if not text or not scores.size or not np.isfinite(scores).all():
            return []
        confidence = float(scores.min())
        if confidence < self.minimum_char_confidence:
            return []
        h, w = image.shape[:2]
        return [([[0,0],[w,0],[w,h],[0,h]], text, confidence)]
