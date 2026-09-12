# OCR validation — 12 September 2026

The optional plate-specific engine improves the tested recorded-video workflow.
It does not establish Indian/government accuracy or on-site readiness.

| Complete recording | Engine | Correct appearances | Incorrect/duplicate observations | Missed appearances | Wall time |
|---|---|---:|---:|---:|---:|
| ParkingGarage, 1,140 frames / 19 seconds | EasyOCR baseline | 2 | 2 incorrect | 2 | 70.20 s |
| Same ParkingGarage recording | Plate ONNX CCT-S-v2 | 4 | 0 | 0 | 65.30 s |
| CarPark, 600 frames / 10 seconds | Plate ONNX CCT-S-v2 | 4 | 1 duplicate | 0 | 43.22 s |

The garage scene was separate from the three development crops used to select the
candidate model. No threshold was retuned after seeing its output. Both garage
runs used the same worker, vehicle/plate models, frame sampling, source format and
new geometric association guard. Original author annotations were used for scoring,
not passed to inference. Upstream model training overlap is unknown. The reused
CarPark scene remains a development diagnostic, not a held-out benchmark.

Each scene contains the same four labelled registrations in different views; these
are eight appearances of four vehicles, not eight independent vehicles. The
CarPark duplicate is penalized: event precision 80%, recall 100%. Garage event
precision/recall are both 100% on only four appearances. These percentages must
always be accompanied by the sample size and scope. No incorrect registration was
confirmed by the optional engine in these two completed runs, but more scenes and
Indian footage remain necessary. Do not describe these results as general accuracy.

The wall times are slower than source duration. This is complete recorded-video
processing, not proof of real-time 60 FPS analytics, alert latency, or multi-camera
capacity. GPU vehicle/plate detection is retained; the new OCR runs on CPU.

## Changes

- Optional `ANPR_OCR_ENGINE=plate_onnx`; EasyOCR remains default and fallback.
- The smallest character score must clear 0.90; averages cannot hide a weak digit.
- Original RGB plate crops feed the plate-specific model. Country/source validation,
  source-quality checks, independent-frame confirmation and durable alerts remain.
- Plate centers and at least 80% of their area must belong to the tracked vehicle;
  padded ROI or full-frame fallback cannot freely borrow a neighboring car's plate.
- Model and configuration SHA-256 checks precede initialization. Downloads are
  explicit during setup. System Status identifies the actual engine and fallback.

The local preview is configured to use the optional engine after these comparisons.
Government cameras retain Indian-format validation; only named public Finnish
recordings have a FINLAND_STANDARD override.

## Reproduce

Install `backend/requirements-plate-ocr.txt`, then run
`python backend/setup_models.py --plate-ocr`. Set the appropriate OCR engine in the
local environment. Existing normal AI models must also be installed.

For an isolated run, from the repository root:

```powershell
.\.venv\Scripts\python.exe backend/benchmark_video.py scratch/public-uvg/ParkingGarage.mp4 --output data/benchmarks/new-garage-run --engine plate_onnx --plate-format FINLAND_STANDARD
```

Use a new output directory for every run. It creates a separate SQLite database,
evidence crops and run.json, leaving working sightings untouched. It refuses an
unavailable requested engine and reports incomplete decoding. Compare the entire
labelled window; duplicates and wrong confirmed observations count as false positives.

Private evidence: `docs/verification/garage-reference-labels.json`,
`garage-ocr-comparison.json`, `carpark-plate-ocr-sept12.json`, and the isolated
`data/benchmarks/` runs. These are not included in the public source repository.
An early harness run used a legacy registry method that lost RECORDED metadata;
it was stopped, marked INVALID_RUN.md and excluded from every result above.

## Provenance

Model: [Fast Plate OCR](https://github.com/ankandrew/fast-plate-ocr),
`fast-plate-ocr==1.1.0`, `onnxruntime==1.30.0`, `cct-s-v2-global-model`.
The upstream project declares MIT; its release URLs and pinned digests are in
`backend/app/services/plate_ocr.py` and `backend/setup_models.py`.
Source recordings and author annotations: [UVG-VCM](https://tie-ultravideo.rd.tuni.fi/UVG-VCM/index.html),
CC BY 4.0, T. Partanen, M. Anttila, R. Kortelahti, G. Gautier, A. Mercat, J. Vanne
(QoMEX 2026). See PUBLIC_SAMPLE_PROVENANCE.md for source hashes and attribution.
