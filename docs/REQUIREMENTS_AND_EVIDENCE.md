# Official requirements and evidence register

Fresh 11 September requests timed out; dates and requirements below are based on saved 5–6 September pages. See SUBMISSION_READINESS.md for the current artifact-by-artifact review.

Source: [official problem statement](https://sentinel.gujarat.gov.in/problems), [FAQs](https://sentinel.gujarat.gov.in/faqs), and [schedule](https://sentinel.gujarat.gov.in/schedule), reviewed 5–6 September 2026. This register distinguishes implementation from demonstrated performance.

Chosen approach: **Model 1 + Model 2**. Registry/GIS is compulsory. Sources connect directly to this platform, while departmental recordings remain at their source. A deployment relay would handle protocol delivery; it would not establish an implemented multi-vendor federation layer.

| Evaluation area / required output | Implementation and evidence | Remaining evidence / limitation |
|---|---|---|
| Camera registry | Validated manual/API onboarding, atomic camera CSV validation, metadata editing and CSV export | Populate accurate organizer metadata |
| GIS | Leaflet map, department/provenance/maintenance filters, camera pins, selected route observations | Basemap requires connectivity; coordinate verification belongs to source owner |
| Health and gaps | Runtime health, metadata report, surveyed polygon union/gap measurements, map overlays and JSON export | Actual surveyed footprints and boundaries are still needed; geometric coverage does not prove plate readability |
| Cross-system viewing | Direct RTSP and HTTP(S) ingestion, local recorded sources and camera grid | Demonstrate two distinct real source systems; configurable source labels alone do not prove interoperability |
| ANPR | Installed vehicle and plate baselines plus EasyOCR run on RTX 3050; two independent qualified frame votes before confirmation | Indian-footage accuracy and designated government plate recognition remain unproven; licensed foreign sample recognition is demonstrated |
| Designated vehicle trace | Registration normalization, durable timestamped sightings, time/source filters, chronological history and map | Two-camera behavior tested using synthetic records; real multi-camera recognition still needs source footage |
| Watchlist correlation | Create/update/deactivate/import records, automatic matching inside the sighting transaction | Representative input is allowed; record labels are not proof of VAHAN/CCTNS connectivity |
| Alerts | Confirmed-match alerts, source/time labels, evidence access, acknowledgement, five-second UI polling | Measure observation-to-alert delay under actual concurrent camera load |
| Evidence report | CSV observations include camera, location, UTC timestamp, class, score, source/session and media offset | No unsupported plate-read accuracy or production-camera count is claimed |
| Working platform | Backend acceptance tests, production frontend build and actual browser workflows | Verification screenshots use an isolated synthetic test database, not a submission demonstration |
| Security | Loopback-only development; configured session authentication, admin/operator/viewer roles, origin checks, evidence containment, redaction and audit events | Department-specific data isolation, durable identity provider and tamper-evident audit storage remain deployment work |
| Architecture | HLD covers direct integration, model pipeline, storage, prerequisites, tradeoffs and regional scaling | Vendor SDK/ONVIF adapters and PostGIS migration are a proposed expansion, not installed features |
| Scale to ~80,000 | Capacity formula, regional deployment, bandwidth/storage assumptions, resilience and cost model | No 80,000-stream load test or single-GPU capacity claim |
| Presentation | Printable solution presentation with current status and clear limitations | Replace validation-pending slides after real-feed measurements |
| Own-feed video | Licensed public Finnish video demonstrates actual onboarding, recognition, a new representative alert, evidence and CSV | Final review/attribution and accessible sharing; this does not establish Indian recognition accuracy |
| Government-feed video | Actual cam06 UI recording, recent CSV download and two-minute report: 89 detection events / 14 session-local tracks, zero confirmed plates | Vehicle detections with timestamps meet the stated report content; ANPR and designated journey remain separate unproven requirements |
| Submission completeness | Checklist, runbook, HLD, source, tests and report paths | Upload final videos/documents and verify viewer access before submitting |

## Acceptance tests performed

11 September revision: **31 passing automated checks**, including PTS expiry, frame-clock behavior, evaluation matching, survey overlap/exclusion/atomicity and coverage roles. The real-browser workflow also passes survey import, a synthetic 50% coverage calculation and report download. The main preview separately displayed actual organizer footage at 1920×1080; no synthetic sightings were inserted into its database.

`backend/tests/test_acceptance.py` verifies camera onboarding, rejection of invalid bulk imports before writes, normalized cross-camera history and restart persistence, alert acknowledgement, low-confidence exclusion from alerts, per-session deduplication, atomic rollback, time/source filtering, no-match behavior, stream URL redaction, evidence containment, edit preservation of private source URLs, role permissions, cross-origin rejection, metadata audit/gaps, missing-ID errors and deadlock-free empty-frame access.

`frontend/browser-check.mjs` drives the installed Edge browser against an isolated server on port 8011: adds a camera and a watchlist entry, searches a two-camera synthetic history, downloads CSV, acknowledges an alert and renders the mobile layout. The fixtures are clearly labelled and never inserted into the main database. Screenshots are under `docs/verification/`.

The existing `scratch/controlled_vehicle_test.mp4` passed a local ingestion test (frames decoded, buffers populated, worker stopped). That is an ingestion check, not a claim of real-world plate-recognition performance.

## Final demonstration acceptance script

1. Start from an empty evaluation database. Record configuration, hardware, model identifiers and source catalogue version.
2. Onboard the authorized feeds. Verify actual connection/frame status and retain source-system identity.
3. Add a representative watchlist record for a readable test vehicle. Explain that it is a supplied test record.
4. Process the original footage; do not manually insert successful sightings. Retain the original recording time and source provenance.
5. Show automatically generated evidence and watchlist alerts. Acknowledge one alert and show its audit event.
6. Search the plate, show ordered camera visits and the map, and export the timestamped CSV. Explain any missing locations or unreadable observations.
7. Restart the backend and repeat the search to demonstrate persistence.
8. Demonstrate no-match and unreadable-plate behavior. Report false positives and misses on labelled footage.

## Submission checklist

- [ ] Team registration/category and chosen Model 1 + Model 2 confirmed in the organizer portal.
- [ ] Presentation updated with actual validation results.
- [ ] HLD reviewed for all implemented/proposed distinctions.
- [x] Public-source recording within the maximum duration shows actual processing, representative watchlist correlation and alerts; final review remains.
- [x] Government-feed recording and timestamped vehicle-detection CSV collected; final content review remains.
- [ ] Accuracy, latency, throughput and recovery report includes method and source data.
- [ ] Videos uploaded as unlisted or viewer-accessible links; test access outside the owner's account.
- [ ] Source/setup package accessible, with secrets excluded.
- [ ] Last-known deadline: 15 September 2026; freshly verifying the portal is still required. Event: 22–23 September 2026; recheck the portal before upload.

Bonus capabilities never substitute for mandatory test and submission evidence.

Latest public-source evaluation: four author-labelled appearances, refined TP 2 / FP 0 / FN 2 on the same diagnostic clip. Baseline and missed labels are preserved. See CURRENT_STATUS.md and PUBLIC_SAMPLE_PROVENANCE.md.
