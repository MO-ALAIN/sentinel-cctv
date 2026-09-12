# Measuring recognition without inventing results

1. Choose a complete time window from an authorized source and record its camera ID and processing session ID from the observations export. Keep source presentation timestamps/media offsets.
2. Independently label every readable target-vehicle appearance in that window, including vehicles the pipeline missed. State your rules for unreadable plates. Do not label only successful output.
3. Create a JSON manifest. The following is a format example, not actual evidence:

```json
{
  "windows": [{
    "camera_id": "YOUR_CAMERA",
    "session_id": "COPY_ACTUAL_SESSION_ID",
    "start_seconds": 100,
    "end_seconds": 160,
    "events": [{
      "plate_number": "GJ01AB1234",
      "start_seconds": 115,
      "end_seconds": 120
    }]
  }]
}
```

4. Run from the repository:

```powershell
.\.venv\Scripts\python.exe backend\evaluate_run.py --database cctv_surveillance.db --labels data\labels.json --output data\evaluation-report.json
```

The evaluator opens the database read-only. It matches at most one confirmed observation per labelled appearance using normalized exact registration and a source-media interval. Extra and incorrect confirmed reads are false positives; unmatched labels are false negatives. Precision is `TP/(TP+FP)`, recall is `TP/(TP+FN)`, and F1 is `2TP/(2TP+FP+FN)`. Undefined metrics are null. Overlapping evaluation windows in the same camera/session are rejected to avoid counting the same evidence twice.

The report includes the label-file hash, explicit matching method, matched IDs, false-positive IDs and missed labels. It does **not** measure per-character OCR accuracy, unlabelled footage, ingestion-to-alert delay, or statewide capacity. Measure those separately with an explicit protocol. Estimated UTC alignment across feeds must be disclosed; it is not verified original recording time.

For a bounded government-stream decode/PTS check:

```powershell
cd backend
..\.venv\Scripts\python.exe probe_stream.py cam04 --output ..\data\stream-check.json
```

The probe suppresses credential-bearing native logs and does not insert observations or download source video files. Its output is an ingestion check, not an ANPR demonstration.
