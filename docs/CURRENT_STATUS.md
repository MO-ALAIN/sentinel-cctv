# Current status — 12 September 2026

## GitHub and hosting

Public source: https://github.com/MO-ALAIN/sentinel-cctv . Add collaborators in
repository Settings. Render configuration, strong generated login passwords,
persistent storage and deployment instructions are included. The first Linux CI
run passed 37 regressions, the frontend build and CPU container build/startup.
An additional health-privacy regression and authenticated AI-readiness smoke test
are included in the follow-up release; check GitHub Actions for its final result.
Render YAML passed the official JSON schema; CPU/GPU Compose configuration passed.
No paid hosting service has been activated and there is no hosted URL yet.

The public repository excludes credentials, databases, videos and evidence captures.
Evidence references below refer to private local artifacts, not public GitHub files.
The working project remains in `E:/gujarat police/repo`; its original Git remote
belongs to the earlier repository. The clean public Git checkout is
`E:/gujarat police/repo/.release/sentinel-cctv`. Publish only reviewed source there;
do not push the original database-containing Git history to the public repository.
Local rollback: `data/before-deployment-20260911-233634.zip`.

## Preview

Open http://127.0.0.1:8000/dashboard/#home on this computer. Use Live Cameras to inspect `cam06` (organizer replay) or reconnect `PUBLIC-CARPARK` (licensed Finnish recording). If the preview stops, double-click START_PREVIEW.cmd in the repository and keep that window open. Only a small measured workload should run on the 4 GB GPU.

## Completed in the latest revision

- Reviewed the saved official problem statement, selected-model deliverables, FAQs, resources and all seven evaluation areas. [Submission readiness](SUBMISSION_READINESS.md) maps each demand to actual evidence and remaining work. Fresh official-site requests timed out; the last-known 15 September deadline is not freshly verified.
- Retained the simple Overview, six main tasks, specialist tools, camera pagination, separate registry sections and all existing investigation controls. Live Cameras now exports actual recent detections with timestamp/source/session information. Assessment failures show a clear error instead of sample measurements.
- Government feed: real cam06 screen recording and a two-minute CSV/JSON report containing 89 detection events, 14 session-local tracks and zero confirmed plate reads. 98/119 health samples reported active frame delivery. Repeated observations are not unique-vehicle counts. This supports the government report's allowance for vehicles OR plates with timestamps.
- Public-source demonstration: original licensed UVG-VCM Car Park footage was onboarded and processed through the real backend. An automatically recognized plate matched a clearly representative watchlist; the video shows the new alert, evidence, acknowledgement and exported history. Updated video: 64.08 seconds; decoder and browser checks passed. This is foreign recorded footage, not an Indian benchmark or multi-camera journey.
- Fixed low-quality OCR votes, valid-vote loss through tiny crops, over-range heuristic scores, deletion of ambiguous embedded OCR characters, and immediate duplicate watchlist notifications. Every sighting remains available for review. Finished recordings are now distinguished from failed frame delivery.
- **31 backend tests pass.** Production build and browser assessment error/recovery checks pass. Both real-source videos exercise the actual interface and export workflow.

## Measured recognition result

The initial full public clip produced two correct appearances, one duplicate observation, one incorrect plate and two misses: event precision/recall 50%/50%. After the measured fixes, replaying all 600 frames produced two correct appearances, no false-positive observations and two misses: precision 100%, recall 50%, F1 66.7% **on only four labelled appearances in that same diagnostic clip**. It is not a held-out result or evidence of broad accuracy. Misses remain unresolved. Old runs and their incorrect observations are retained as evaluation evidence, separated by session.

The independent label manifest, exact matches/misses and baseline/refined reports are in docs/verification. Source attribution, download hashes, the limited Finnish camera format and representative watchlist scope are in [Public sample provenance](PUBLIC_SAMPLE_PROVENANCE.md).

## What remains before a strong submission

1. Improve and independently validate Indian-plate recognition on complete readable windows, including misses, false matches and end-to-end delay. No government plate has been confirmed in the reported window.
2. Demonstrate actual source-system interoperability and a real cross-camera designated-vehicle journey. One public file plus one organizer gateway does not establish two integrated departmental VMS systems.
3. Obtain verified camera coordinates, department/ownership/storage metadata and survey boundaries/footprints. Thirty organizer records have IDs/names but no supplied coordinates; geographic coverage remains unmeasured.
4. Measure sustainable concurrent capacity, reconnect/restart recovery, latency and resource use. The approximately 50 evaluation cameras and 80,000-camera design target are not demonstrated laptop capacity.
5. Review both videos with their reports, finalize presentation/HLD, verify team/portal fields and viewer-accessible links, and submit before the freshly checked deadline. **No competition submission has been made. The source code is now public on GitHub; demo artifacts remain local.**

Department/case isolation, organizational identity, retention enforcement, tamper-evident evidence and regional rollout remain production work. The architecture document distinguishes these proposals from implemented local controls.

## Artifacts and rollback

- [Public-source demonstration](verification/public-source-demonstration.webm), [matching report](verification/public-source-demonstration.json), [history CSV](verification/public-source-history.csv).
- [Government demonstration](verification/government-preview-draft.webm), [detection CSV](verification/government-detections-sept11.csv), [bounded run](verification/government-detections-sept11.json).
- [Refined sample evaluation](verification/public-source-evaluation-refined.json), [baseline evaluation](verification/public-source-evaluation.json).
- [Solution presentation](SOLUTION_PRESENTATION.pdf), [high-level design](HIGH_LEVEL_DESIGN.md), [full readiness review](SUBMISSION_READINESS.md).

Original rollback: E:\gujarat police\.rollback\checkpoint-20260905-233347.zip. Later source snapshots are in ignored repo/data, including before-evidence-20260911-142701.zip and before-recognition-refinement-20260911-201538.zip. Preserve current data/evidence separately before restoring.
