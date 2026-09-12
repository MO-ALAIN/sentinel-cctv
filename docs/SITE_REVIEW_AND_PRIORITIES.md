# Requirements revision — 11 September 2026

## What we are building, in plain language

The challenge is to bring separate departmental camera systems into one usable workspace. A police operator should be able to find cameras, view an authorized feed, search a registration number, see where and when it was observed, and review an alert when a confirmed observation matches a supplied watchlist.

Our selected architecture is **Model 1 + Model 2**. Model 1 is the compulsory camera inventory and GIS foundation. Model 2 adds direct viewing and selective analytics while existing departmental recording systems continue operating. We should demonstrate this combination clearly before adding optional analytics.

## Sources rechecked

- [Problem statement and seven-step submission guide](https://sentinel.gujarat.gov.in/problems): functional requirements, test case, deliverables and qualitative evaluation.
- [FAQs](https://sentinel.gujarat.gov.in/faqs): mandatory Model 1, direct-integration Model 2, dataset versus evaluation-camera counts, demonstration requirements and phase progression.
- [Public integration resources](https://sentinel.gujarat.gov.in/resource): TCP transport, presentation timestamps, reconnect behavior, heterogeneous streams and looping footage.
- [Home and announcements](https://sentinel.gujarat.gov.in/), [phases](https://sentinel.gujarat.gov.in/phases), and [contact](https://sentinel.gujarat.gov.in/contact): current deadline, event, programme and support context.
- The authenticated camera portal's `/resource` guide: actual deployment endpoints and credential requirements. Its saved copy is private under `data/`; credentials are not part of submission documents.

This revision uses saved official problem, FAQ, resource, home, phase and contact pages retrieved on 5–6 September in `../project-review`. Fresh requests on 11 September to the public site timed out; `verification/site-20260911/retrieval.json` records this failure. The last-known submission deadline is **15 September 2026**, shortlisting that evening, and event **22–23 September**. These dates have not been freshly verified. About and Schedule could not be freshly read. No upload, registration change or submission has been performed.

## Submission versus on-site evaluation

The own-feed screen recording is limited to 2–3 minutes and must show a working backend: onboarding, analytics, correlation with a representative watchlist and automatic alerts. A permitted public recording can be considered as footage of our choice, with attribution and an honest source label; a seeded database or animated scene is not evidence of recognition.

The government-feed submission requires onboarding, viewing, available analytics and a report of **detected vehicles or number plates with timestamps**. Its report does not have to invent successful plate recognition to be useful. This narrower submission requirement does not remove Model 2's ANPR deliverable or the on-site designated-vehicle challenge.

At evaluation, the organizer supplies a designated registration. The system must trace its actual appearances across cameras with time/location history and show continuous watchlist correlation with automatic alerts. Approximately 50 evaluation cameras differ from the 30-camera authenticated catalogue currently available. The FAQs describe 30+ recordings from five departments and a common replay timeline; per-camera count is not a throughput guarantee.

Model 1 is compulsory with at least one additional model. We chose Model 2 direct source integration. Model 3 vendor federation and Model 4 full central recording/advanced biometrics are different architectures, not extra mandatory implementations for our selected combination. The general statewide sizing, security, interoperability and demonstration requirements still apply.

See [the complete submission checklist](SUBMISSION_READINESS.md) for model-specific deliverables and all seven evaluation areas.

## Important deployment differences discovered

The public guide describes `/api/ingest`. The authenticated deployment instead documents and serves `/cameras.json`; `/api/ingest` returned 404 after login. Its manifest currently contains **30 camera IDs and names**, without coordinates, department assignments, codec or resolution metadata. The adapter uses the live manifest and that deployment's documented URL pattern, and preserves missing fields as unknown.

The approximately 50 cameras described for the evaluation are a separate target from the current 30-camera catalogue. Neither number is a fixed application limit or proof that all cameras have been successfully processed.

The deployed RTSP gateway requires a percent-encoded registered email and access password. Authentication is added at connection time; camera exports redact credentials. One camera, `cam04`, passed a bounded authenticated RTSP probe: 36 decoded frames, 1920×1080, 35 increasing PTS transitions and no PTS regression. See `verification/organizer-stream-check.json`. This proves ingestion for that test, not ANPR accuracy or continuous availability. The authenticated HLS request returned 403, so HLS fallback on this deployment is not yet proven.

## Priorities for a stronger submission

These are our engineering priorities inferred from the official criteria, not published scoring weights. The site gives qualitative criteria and does not guarantee selection for any particular feature set.

| Priority | Official area | Evidence we need |
|---|---|---|
| 1 | Successful test case | Government camera onboarding, live viewing, actual analytics and timestamped output |
| 2 | Video analytics output | Correct plate reads, documented misses/false matches, evidence crops and a designated-vehicle history |
| 3 | Working platform | Repeatable operator workflow on both own-source and government feeds; persistence and recovery |
| 4 | Architecture | Model justification, direct integration, department prerequisites, security boundaries and realistic sizing |
| 5 | Presentation | Concise, consistent explanation supported by real screenshots and measurements |
| 6 | Scalability and PoC readiness | Measured per-worker capacity, regional expansion, bandwidth/storage arithmetic and a recovery plan |
| 7 | Submission completeness | Presentation, HLD, required videos, output report and accessible links |

Bonus features cannot replace mandatory evidence. Thirty feeds from one sandbox do not by themselves prove integration with two different VMS/source systems. A configurable source-system label is not interoperability evidence.

## Implemented and verified so far

- Camera manual/API/CSV onboarding, validation, editing, exports and audit history; GIS markers distinguish verified, representative and unknown coordinates. Filters cover department, type, connection, maintenance and coordinate provenance.
- Actual RTSP ingestion, browser viewing, bounded buffers, reconnect backoff, source labels and honest health reporting. Timed processing uses PTS; source-time conversion is exact only when the source's UTC origin is known. Otherwise the timestamp basis is explicitly `PTS_ESTIMATED_UTC`.
- Separate per-camera/session tracking, durable normalized observations, transactional watchlist matching, alert acknowledgement, search filters and CSV evidence reports.
- Independent-frame OCR confirmation and partial-registration rejection; uncertain results cannot become confirmed watchlist alerts through the normal pipeline.
- Local access restrictions, authenticated admin/operator/viewer sessions, cross-origin mutation checks, private-source redaction and constrained evidence paths.
- Thirty-one automated checks at this revision, production frontend build, synthetic workflow browser checks, and a real browser preview showing the 30-camera registry and decoded organizer video. Synthetic fixtures stay in a separate test database.
- Verified-survey polygon import, equal-area union/gap measurements, map overlays, report download and audited removal; overlapping footprints do not double count and representative features do not contribute to measurements.
- An evaluator that compares confirmed observations with independently labelled camera/session/media intervals. It penalizes incorrect and duplicate reads and reports misses; an empty prediction set is not treated as perfect accuracy.

## Remaining evidence and implementation limits

1. GPU/model setup is complete and organizer decode → detect → track → OCR is executing on the RTX 3050. Benchmark the remaining successful recognition → persist → alert path on suitable readable footage; model readiness alone is not accuracy evidence.
2. Validate plate localization and recognition on actual organizer scenes, including unreadable cases. Keep source/model provenance and label a complete evaluation window, not only successful examples.
3. Demonstrate actual cross-camera recognition and a designated plate history. Synthetic repository tests prove query behavior; they do not prove real multi-camera recognition.
4. Obtain verified coordinates, departmental metadata, coverage polygons and area boundaries. Survey-based geographic gap computation is now implemented and tested, but real organizer survey data is absent.
5. Show a second independently sourced system for the Model 2 interoperability deliverable.
6. Supply suitable own-source footage and record the separate own-feed demonstration (maximum 2–3 minutes). The supplied drawn test video and missing historical VisDrone paths are not substitutes for this evidence.
7. The 11 September government recording and timestamped detection CSV are now collected. Review the recording and its limitations before final sharing; real ANPR and the separate own-feed/watchlist demonstration remain outstanding.
8. Department/case-scoped authorization, organizational identity, tamper-evident evidence, enforced retention and a regional production deployment remain work beyond the current shared prototype.

## Technology choices and why

| Layer | Current implementation | Appropriate next step |
|---|---|---|
| Operator UI | React + Leaflet | Retain it; clear investigation workflows matter more than a UI framework migration |
| APIs | FastAPI | Retain the explicit API contract; add department-scoped authorization before departmental rollout |
| Registry/geo/history | SQLite WAL for the local prototype | PostgreSQL + PostGIS for concurrent regional use and real spatial coverage queries |
| Video | OpenCV/FFmpeg, RTSP over TCP, MJPEG preview | GStreamer/DeepStream on suitable regional hosts; WebRTC/HLS browser relay after actual integration tests |
| Detection/tracking | Small YOLO baseline, PTS-aware ByteTrack adapter | Benchmark newer small YOLO variants and TensorRT; choose using measured end-to-end accuracy, VRAM and latency |
| Plate recognition | Plate localization + EasyOCR + independent-frame agreement | Compare a plate-specific recognizer on held-out Indian footage; do not replace measurement with model-card scores |
| Events/evidence | Transactional SQLite writes and local crops | Transactional outbox, Kafka, regional retry queues and S3-compatible evidence storage |
| Identity/operations | Local sessions and roles | Organizational OIDC, department/case scopes, managed secrets, monitored backup/restore and regional orchestration |

The current GPU has 4 GB VRAM. Start with a small number of streams and report measured capacity. Do not claim that one laptop can process 50 or 80,000 cameras. The official technology suggestions are references, not compulsory products; choose tools that support the demonstrated architecture and operational requirements.
