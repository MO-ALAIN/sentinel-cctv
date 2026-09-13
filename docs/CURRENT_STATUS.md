# Current status — 14 September 2026

## Final engineering revision — 14 September 2026

The local backend suite passes **62 tests**. Temporary OCR state now stores quality
metadata instead of retaining full video frames and is limited to 1,000 recently used
tracks by default. Confirmed sightings remain durable, including after cache eviction.
A controlled 12-track test retained 74,649,600 source-image bytes before the change
and zero after; this measures retained source arrays, not whole-process RAM.

Confirmation uses a bounded window of independent qualified reads, rejects invalid
confidence and weak OCR segments, and associates confidence with the winning plate.
Camera resets use exact camera identity. Reading diagnostics never starts capture;
explicit diagnostic jobs require an operator and run off the API event loop, with
one diagnostic job at a time. Recognition queries also remain off the event loop.

Both complete foreign-video regressions preserved TP4/FP0/FN0: CarPark, 600 frames
in 55.45 seconds; ParkingGarage, 1,140 frames in 104.34 seconds. These reused scenes
contain the same four vehicles. They do not establish Indian accuracy, independent
VMS interoperability, or real-time throughput. Timings are slower than the earlier
runs; no speed improvement is claimed. See OCR_VALIDATION.md for history.

Rollback: `data/before-final-anpr-sept13.zip` and matching database snapshot.

## Camera shutdown responsiveness

Slow camera shutdown now runs outside both the API event loop and shared camera
registry lock. Other source/status requests remain available. Reconnect is rejected
while a previous worker is stopping, unfinished workers remain registered/countable,
and shutdown still attempts other sources after a stop timeout. The automated suite
now passes **49 tests**, including controlled slow-stop and concurrent HTTP checks.
The preceding admission/recovery release passed all GitHub checks:
https://github.com/MO-ALAIN/sentinel-cctv/actions/runs/34735988900 .
Rollback: `data/before-responsive-stop-sept13.zip`.

## Latest reliability revision

Configurable unified camera-worker admission now defaults to two. Concurrent
connects cannot overrun that limit; ended recordings free a slot, and stalled
sources remain disconnectable in the interface. The limit is a resource safeguard,
not a proven throughput rating. Local validation: **46 backend tests**, frontend
build and both browser checks pass.

A real 60-second organizer-plus-recording run had zero sampled API errors; median/
maximum health latency was 6.63/452.82 ms. CarPark decoded all 600 frames and produced
four known plate observations. The organizer report contained two vehicle events
and no confirmed plate. Actual process restart preserved 40 sightings, 2 watchlist
entries and 19 alerts; the selected network feed resumed and the recording stayed
stopped. See [runtime evidence and limitations](RUNTIME_VALIDATION.md).

The preceding NMS release passed Linux CI:
https://github.com/MO-ALAIN/sentinel-cctv/actions/runs/34693387638 . The reliability
revision's CI result should be checked on the latest GitHub commit before freezing.
Rollback: `data/before-workload-limit-sept13.zip` and matching `.db`; interface
rollback: `data/before-stalled-controls-sept13.zip`.

## GitHub and hosting

Public source: https://github.com/MO-ALAIN/sentinel-cctv . Add collaborators in
repository Settings. Render configuration, strong generated login passwords,
persistent storage and deployment instructions are included. The earlier OCR Linux CI
run passed all 43 regressions, the frontend build, CPU container build/startup,
authentication checks and readiness checks for vehicle detection, plate detection
and OCR. Verified run: https://github.com/MO-ALAIN/sentinel-cctv/actions/runs/34692539002 .
Render YAML passed the official JSON schema; CPU/GPU Compose configuration passed.
No paid hosting service has been activated and there is no hosted URL.
The user chose free operation on 12 September: cloud deployment is deferred.
The saved official guide makes the hosted URL optional; fresh checks of home,
problems, FAQs and phases on 12 September all timed out. The complete app remains
local with the RTX 3050, while GitHub provides free source collaboration.
Next priorities are measured recognition, the two required demonstrations/reports,
consistent presentation/HLD and accessible submission links.

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
- **43 backend tests pass in Linux CI for the OCR release.** Production build and browser assessment error/recovery checks pass. Both real-source videos exercise the actual interface and export workflow.

## Latest tracking and organizer checks

Cross-class vehicle box suppression removed the duplicate in the complete CarPark
regression: TP 4 / FP 0 / FN 0, 600 frames in 36.19 seconds. The complete garage
regression retained TP 4 / FP 0 / FN 0, 1,140 frames in 61.33 seconds. These are two
reused foreign scenes with four shared vehicles; no Indian/general accuracy claim.
All 43 backend tests passed locally after this change. See OCR_VALIDATION.md for
previous results, retained false-positive evidence and overlap-related limitations.

A fresh sequential survey checked 29 organizer feeds: 22 decoded an image, 21 had
advancing timestamps. Two bounded app checks produced 5 and 13 detection events,
respectively, with zero confirmed plates. See ORGANIZER_SOURCE_CHECK.md. Readable
Indian plates and genuinely different VMS evidence remain the main analytics gaps.

## Recognition improvement on 12 September

The local app now uses optional pinned CCT-S-v2 plate OCR on CPU, with GPU vehicle/
plate detection and the existing source-format, quality and independent-frame
confirmation gates. EasyOCR remains the default for unconfigured installs and the
fallback if the optional engine is unavailable. The UI reports the actual engine.

On the separate complete ParkingGarage recording (1,140 frames), EasyOCR produced
TP 2 / FP 2 / FN 2. The optional engine produced TP 4 / FP 0 / FN 0, in 65.30 seconds
versus 70.20 seconds. On the reused complete CarPark recording (600 frames), the
optional engine produced TP 4 / FP 1 / FN 0; the false positive was a duplicate
observation, not an incorrect string. Its event precision/recall are 80%/100%.
These are eight appearances of four vehicles across two Finnish scenes. Upstream
training overlap is unknown; no Indian or government accuracy claim is made.
See [full methodology and limits](OCR_VALIDATION.md).

The actual local app also decoded all 1,140 garage frames, recognized the four
plates, generated two automatic representative watchlist alerts, and returned
ZPN720 history across PUBLIC-CARPARK and PUBLIC-GARAGE. Browser verification passed.
This proves matching across two real recorded scenes, not a verified original-time
journey, geographic route or integration with two departmental VMS products.
Locations and original recording times remain unknown. The interface now keeps
observations visible instead of showing a large empty map when coordinates are absent.

Plate association now rejects candidates outside the tracked vehicle, including
neighboring plates in ROI padding and full-frame fallback. New regression cases
cover that behavior and weakest-character confidence/color handling. **43 backend
tests, the frontend build and the real two-recording browser check pass locally.**
The public CI run for the new release must also pass before acceptance.

Earlier evaluation reports, including incorrect observations, are preserved under
`docs/verification`; the previous 31/38-test results and demo videos are historical.
The saved deadline plan is [DEADLINE_PLAN.md](DEADLINE_PLAN.md): build/validate on
12–13 September, final evidence and documents on 14 September, submission checks
on 15 September. The initial presentation/HLD drafts already exist.

## What remains before a strong submission

1. Improve and independently validate Indian-plate recognition on complete readable windows, including misses, false matches and end-to-end delay. No government plate has been confirmed in the reported window.
2. Demonstrate actual source-system interoperability and a designated-vehicle journey with verified original time/location. Two public recordings now match through real recognition; they do not establish two integrated departmental VMS systems.
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
