# Installed model provenance — 8 September 2026

These are downloaded baselines, not models trained by this team. Their authors' benchmark numbers are not results on the Sentinel streams.

| Component | Installed baseline | Source |
|---|---|---|
| Vehicle detection | YOLOv8n, COCO vehicle classes | [Ultralytics release](https://github.com/ultralytics/assets/releases/tag/v8.3.0) |
| Plate localization | YOLOv8s, one plate class | [Pinned model card](https://huggingface.co/Babblu2821/alpr-plate-detector/blob/4ae32c182f083f1a60c3a8c1a19ad82b2674eea3/README.md) |
| OCR | EasyOCR English generation 2 + CRAFT text detector | [EasyOCR project](https://github.com/JaidedAI/EasyOCR) |
| Execution | Torch 2.6.0+cu124, torchvision 0.21.0+cu124, Ultralytics 8.4.142, EasyOCR 1.7.2 | See installed dependency snapshot |

The plate checkpoint is pinned to revision `4ae32c182f083f1a60c3a8c1a19ad82b2674eea3` and SHA-256 `f05ae9d42f9f88757670f5f333f128a64738419d746393c8c9d09c0801af6e8d`. Setup checks its digest and restricts checkpoint globals to approved model classes before installation. The model card declares MIT and describes mixed plate imagery; see its retained copy under `verification/plate-model-card.md`. Ultralytics software has its own AGPL/enterprise licensing terms; the card's declaration does not replace dependency licensing. EasyOCR is distributed under Apache-2.0. Preserve upstream notices with distributions.

Runtime health on this workstation confirms vehicle model readiness on the RTX 3050 Laptop GPU, trained plate detector readiness, and GPU-enabled OCR. This proves initialization and observed execution, not plate accuracy. Independent ground-truth labels, misses, false matches, performance across scenes and sustainable concurrency remain required. Night glare, small plates and source compression can remove the details OCR needs.

To install the same baselines after AI dependencies:

```powershell
.\.venv\Scripts\python.exe backend\setup_models.py --plate-detector
```

No original government video files were downloaded. The application consumes the authorized stream; evidence screenshots are captures of the working interface.


## Optional plate OCR added 12 September

[Fast Plate OCR](https://github.com/ankandrew/fast-plate-ocr) 1.1.0,
CCT-S-v2 global model, ONNX Runtime 1.30.0 on CPU. The project declares MIT.
Model/config SHA-256 values are enforced in `backend/app/services/plate_ocr.py`.
Original release URLs are in `backend/setup_models.py`; downloads are explicit.
This is another pretrained baseline, not team-trained. OCR_VALIDATION.md reports
our own separate-scene comparison, duplicate penalty and unknown upstream data overlap.
The current local preview uses CPU plate OCR; earlier GPU EasyOCR reports are historical.
