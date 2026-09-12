# Submission readiness — 12 September 2026

## Understand the challenge

Bring separate departmental cameras into one operator workspace. Maintain a reliable camera inventory, view authorized sources, extract useful vehicle observations, search a registration across cameras and generate an automatic alert when a confirmed observation matches a representative watchlist. A good interface supports this workflow; the judges also need real working evidence.

**Selected architecture: Model 1 + Model 2.** Model 1 supplies compulsory registry/GIS. Model 2 directly consumes permitted departmental feeds while their VMS and recording systems continue to operate. We have not built Model 3 vendor federation or Model 4 full central recording. Suggested technologies on the site are examples, not a compulsory shopping list.

## Authority and dates

Reviewed the complete saved [problem statement](https://sentinel.gujarat.gov.in/problems), [FAQs](https://sentinel.gujarat.gov.in/faqs), [resources](https://sentinel.gujarat.gov.in/resource), [home](https://sentinel.gujarat.gov.in/), [phases](https://sentinel.gujarat.gov.in/phases), schedule and contact material in `../project-review`, retrieved 5–6 September. Public site requests on 11 September timed out, including About and Schedule; retrieval failures are preserved in `verification/site-20260911/retrieval.json`. No claim is made to have freshly read unavailable content.

Last-known dates: submission **15 September 2026**, shortlisting that evening, event **22–23 September** and results **23 September**. Recheck the logged-in portal before submission. Category eligibility, team registration, and uploaded links have not been verified for this team. The FAQ describes separate academic/student/startup and enterprise categories; registration details must match the team's actual eligibility. Selection is competitive and no numeric scoring weights or guarantee were published in the reviewed material.

## Model-specific deliverables

| Requirement | Current evidence | Still needed |
|---|---|---|
| Model 1 working registry and GIS | Validated metadata, map, filters, maintenance/health, coordinate provenance | Verified locations for organizer cameras; all 30 currently lack coordinates |
| Bulk/manual/API onboarding | Working forms, atomic CSV validation, API and audit; isolated browser tests | Record the manual and bulk workflow in final presentation/demo |
| Sample metadata dataset | Real catalogue IDs/names; registry export available | Verified department, owner, storage and infrastructure data |
| Registry API documentation | CONTRACT.md and running `/docs` OpenAPI | Package/reference the current contract in the final links |
| Gap-analysis report | Metadata gaps and verified polygon union/uncovered-area report implemented and tested | Owner-supplied boundaries/footprints; no geometric area percentage can be claimed for missing surveys |
| Role-based search/filter/export/audit | Local admin/operator/viewer enforcement; origin and evidence controls | Department/case isolation and organization identity for rollout |
| Model 2 viewer from at least two different systems | Direct RTSP/HTTP/file support; one real organizer gateway demonstrated | Record an actual second independent source integration; different camera IDs or labels alone are insufficient |
| ANPR on live or recorded footage | GPU vehicle/plate detector and OCR; independent qualified-frame confirmation | Correct real recognition and independently measured accuracy |
| Searchable movement metadata | Durable observations, time/source filters, ordered visits, evidence, CSV | Actual recognized multi-camera journey; current seeded workflow tests are not camera evidence |
| Architecture preserving existing systems | HIGH_LEVEL_DESIGN.md direct ingestion, selected evidence, departmental recording retained | Vendor/source-specific feasibility evidence and prerequisites |

## All seven evaluation areas

These are the site's common qualitative areas; the order below is not a published weighting.

| Area | Evidence prepared | Remaining acceptance condition |
|---|---|---|
| 1. Successful test case | 30 organizer records, actual cam06 decode/view/GPU detection, timestamped CSV and video | Strengthen recognition and prepare the designated-vehicle test; source health is intermittent |
| 2. Solution presentation | Eight-slide PDF/HTML explaining model, workflow, technologies, benefits and limits | Public-source evidence added; independently validate Indian recognition and capacity |
| 3. Solution architecture | Component diagram, heterogeneous ingress, security, source prerequisites, scale and cost worksheet | Concrete vendor/department data, measured sizing and priced infrastructure proposal |
| 4. Working platform and demonstration | Local application, 43 backend checks, simple navigation and actual government UI capture | Public-source analytics → watchlist → alert video now recorded; final review and Indian recognition validation remain |
| 5. Video analytics output | 89 government detection events in a bounded 120-second window; source/session/time-basis columns | Label complete windows; measure exact-match precision/recall, misses, false alerts and latency |
| 6. Scalability and PoC readiness | Regional/edge plan, bandwidth/storage arithmetic, retries, buffer bounds | Complete-pipeline concurrency, recovery drills and resource measurements; 50 and 80,000 are targets, not demonstrated capacity |
| 7. Submission completeness | Local presentation, HLD, source, runbooks, government video and reports | Final video review, consistent accessible links, portal fields and actual submission |

Bonus features must be relevant, working and demonstrated. They do not compensate for mandatory failures. Existing health, GIS, event and dashboard tools remain accessible, but adding extra pages or face recognition would not solve the present evidence gaps.

## Three demonstrations to keep distinct

| Stage | Required content | Present status |
|---|---|---|
| Own-feed submission video | Maximum 2–3 minutes; onboard/process chosen real footage, analytics, representative watchlist correlation and automatic visible alert | Licensed public Finnish video demonstrates a new automatic representative match, evidence and history export; original source attribution retained |
| Government-feed submission video + report | Onboard organizer source, view it, show available analytics; report detected vehicles **or** number plates with timestamps | Local video and actual vehicle CSV collected on 11 September; zero confirmed plate reads disclosed |
| Evaluation designated-vehicle challenge | Registration supplied at evaluation; identify and trace actual camera appearances with time/location history; continuous watchlist match and real-time alerts | Query/alert behavior tested with isolated synthetic fixtures; real multi-camera recognition remains unproven |

The government report's allowance for vehicle detection does not eliminate the selected model's ANPR requirement. The map displays ordered camera observations; it cannot reconstruct unobserved roads or fabricate missing locations. The organizer's replay source needs presentation timestamps; estimated UTC must not be described as verified original capture time.

## Current evidence package

- `verification/government-preview-draft.webm`: 65.92-second, 1440×960 actual UI screen recording, decoded successfully; no browser JavaScript errors. Shows registry, daylight organizer video, CSV export, health and coverage limitations.
- `verification/government-preview-output.json`: timestamped runtime, registry, recognition and recent-detection snapshot from that recording.
- `verification/government-ui-detections-sept11.csv`: the report downloaded through the visible UI button.
- `verification/government-detections-sept11.csv` and `.json`: bounded run from 09:09:03 to 09:11:03 UTC; 89 detection events, 14 session-local tracks, five sessions; 98/119 health samples reported streaming, zero API errors and zero confirmed plates. Observed classes: motorcycle and truck. These are model outputs, not independently verified ground truth.
- `verification/government-summary-sept11.json`: compact computed evidence/video summary.
- Automated suite: 43 passed; frontend production build passed. New checks cover export scope/provenance, formula escaping, empty exports, low-quality OCR exclusion and preservation of valid votes through intervening bad crops.

The original rollback remains `E:\gujarat police\.rollback\checkpoint-20260905-233347.zip`. Today's pre-edit source snapshot is `data/before-evidence-20260911-142701.zip`. Preserve current database/evidence separately before any restore.

## Technologies suited to this work

| Layer | Use now | Expansion after measurement |
|---|---|---|
| Interface/GIS | React + Leaflet, clear task navigation | Retain; optimize large map inventories and accessibility |
| API and records | FastAPI + SQLite WAL for local proof | PostgreSQL/PostGIS and department-scoped authorization |
| Video | OpenCV/FFmpeg RTSP TCP, bounded workers, MJPEG preview | Tested GStreamer/DeepStream pipelines and WebRTC relay for selected live views |
| AI | Small YOLO, camera-isolated ByteTrack, plate baseline, EasyOCR on RTX 3050 | Compare plate-specific OCR and TensorRT against held-out Indian footage before adopting |
| Events and evidence | Transactional sighting/match/alert, local crops and audit | Transactional outbox, durable regional queues/Kafka and object storage |
| Deployment/security | Loopback preview and optional local roles | OIDC, encrypted transport/storage, managed secrets, retention and recovery drills |

These are an engineering direction, not a claim that every proposed product is deployed or benchmarked. Keep the 4 GB GPU focused on a small measured workload. Budget central/regional/edge compute, accelerator capacity, bandwidth, hot/warm/cold retention, failure capacity, monitoring, backup/DR and operating costs using measured rates and actual quotes. HLD includes the sizing formulas and department information checklist.

## Finish in this order

1. Review the completed public-source video and its attribution/report. Keep foreign footage distinct from Indian accuracy evidence.
2. Label full Indian/government test windows independently, then fix measured recognition failures. Include unreadable vehicles, misses and false positives; do not tune on the final held-out test.
3. Demonstrate two genuine source systems and a real multi-camera journey; obtain verified camera location/department/survey data.
4. Run bounded complete-pipeline capacity/reconnect/restart checks and report workload, VRAM, health and latency limitations.
5. Update presentation/HLD with final evidence, review videos/reports for consistency, create permitted viewer links, verify access outside the owner's account and submit through the portal. Nothing is uploaded or submitted yet.

Allowed video link options from the saved guide: unlisted YouTube or Google Drive/OneDrive with Anyone-with-link Viewer access. Hosted platform/test credentials and GitHub/GitLab source are additional options. Keep all source access credentials and local private configuration out of the shared package.

## Latest completed public-source evidence

`verification/public-source-demonstration.webm` and its JSON/CSV show real manual onboarding, processing, a new representative watchlist alert, saved crop, acknowledgement and history export. The source is licensed Finnish footage, not the team's own capture. See PUBLIC_SAMPLE_PROVENANCE.md. All 600 source frames were decoded in the refined run.

Four complete author-labelled plate appearances were evaluated. Baseline: TP 2 / FP 2 / FN 2. Refined diagnostic replay: TP 2 / FP 0 / FN 2. Precision improved from 50% to 100%; recall stayed 50%. Only this small reused clip is covered; Indian accuracy remains unproven. The two-second repeat-alert rule retains observations, so it does not hide duplicate sightings from the evaluator. The partial/incorrect historical reads remain in their original sessions.


## Hosting decision, 12 September

Deployment is optional in the saved official submission guide: participants
"may additionally provide a URL to their hosted platform". Source: saved
`../project-review/sentinel-problems-2026-09-06.txt`, lines 547-550. Today's direct
requests to home, problems, FAQs and phases timed out; retrieval evidence is private
under `docs/verification/site-20260912/retrieval.json`. Recheck for changes before
submitting. Keep the full app on the local RTX 3050 without hosting charges.
GitHub collaboration is available at https://github.com/MO-ALAIN/sentinel-cctv .

Required submission work remains presentation (PPT/PDF), HLD, own-source video,
government-source video plus timestamped output report, and reviewer-accessible
links. Cloud hosting is not a current priority and does not replace any of these.


## 12 September engineering progress

See OCR_VALIDATION.md for the measured new engine: garage TP4/FP0/FN0 on a separate
four-appearance scene, and reused car-park TP4/FP1-duplicate/FN0. Actual app operation
now matches ZPN720 across two public recordings and produces new representative
alerts. Original timestamps, locations, government plate accuracy and two-VMS
interoperability remain unverified. Final submission videos/documents are scheduled
for 14 September; do not substitute these small foreign-scene percentages for an
Indian benchmark. New local suite: 43 passed; build and real browser check passed.
