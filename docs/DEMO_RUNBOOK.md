# Demonstration and operator runbook

1. Start the application with `START_PREVIEW.cmd` from the repository. Open http://127.0.0.1:8000/dashboard/ . Open More tools → System status to check actual AI readiness.
2. In Camera registry, onboard authorized source URLs or a local recording filename. Local files live under `scratch/` by default. Set RECORDED for files and GOVERNMENT_REPLAY for organizer replay streams. Supply known source-recording start time in UTC when available. Do not mark illustrative coordinates VERIFIED.
3. Use Import organizer catalogue only after configuring the current endpoint and authorized access in `backend/.env`. An empty catalogue or sign-in page does not prove any camera connected. The app does not register an account for you.
4. Select Connect for a camera, then inspect Live Cameras and actual frame/connection state. No local recording replaces failed RTSP automatically.
5. Add a representative watchlist entry whose plate is actually readable in your footage. Use an accurate source description such as MANUAL_TEST. Do not claim a live government-database integration.
6. Show automatic recognition, the saved evidence crop and the resulting alert. If the source is unsuitable for OCR, report that outcome and demonstrate vehicle detection separately.
7. Open Find vehicle, enter the plate, show the chronological table and map, filter by time/source, and download the observation CSV. Explain dashed observation links and gaps.
8. Restart the application and repeat the query. Acknowledge an alert and show audit history.

## Suggested 2–3 minute recording

- 0:00–0:25: source identity, onboarding and actual video.
- 0:25–1:05: readable vehicle appears, automatic ANPR and representative watchlist match.
- 1:05–1:40: alert evidence, second camera observation and timestamped map/history.
- 1:40–2:10: export and restart persistence.
- 2:10–2:40: limits, source provenance and actual measured results.

Record your own feed and the government feed as the organizer requests. The isolated browser-test screenshots and manually seeded test records are development verification, not these submission demonstrations.

## Recovery

- Backend unavailable: run `START_PREVIEW.cmd` and inspect terminal output; verify port and API base.
- AI unavailable: install the AI requirements and download approved weights via `backend/setup_models.py`; restart. Model setup uses E: paths by default in this workspace.
- Camera unavailable: verify authorized access, network and source URL. Recorded sources must exist inside the media directory.
- Map tiles unavailable: table/coordinates remain usable; configure an approved tile provider for deployment.
- Missing evidence: original crop was not saved or was removed. Do not replace it with a generated image.
- Rollback: original checkpoint is outside the repo under `.rollback/`. Stop the app, preserve any newer database/evidence, and restore into a separate folder for comparison before replacing working data.

## Government-feed recording and report

The official government submission allows detected vehicles OR number plates with timestamps. Show Camera registry → the real organizer catalogue, Live Cameras → an actually connected source → View Details, then Export recent detections. Show System status and accurately describe unreadable plates. Do not claim a designated journey from detection boxes alone.

For a bounded report, run from backend: `..\.venv\Scripts\python.exe record_detection_report.py cam06 --seconds 120 --output ..\docs\verification\government-detections-sept11`. It excludes observations already buffered at start and polls new events. Leave only the selected source processing on the 4 GB laptop unless capacity has been measured.

From frontend, `node record-government-preview.mjs cam06` records the actual UI and tests its download button. The generated CSV, JSON and video under docs/verification are local artifacts, not uploaded links. The 11 September run contains 89 detection events across 14 session-local tracks and zero confirmed plate reads. UTC timestamps marked PTS_ESTIMATED_UTC are reception-anchored estimates, not the camera's June timestamp overlay.

For the own-source video, a licensed public clip must retain attribution and source identity. Foreign-format samples can verify workflow only after a separately configured format is supported; do not weaken Indian validation globally or present them as an Indian-footage accuracy test. Never repeat a still image to manufacture independent recognition evidence.
