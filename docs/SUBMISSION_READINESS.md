# Submission readiness — 14 September 2026

## Build selected for the demonstration

Model 1 + Model 2: camera registry/GIS plus direct authorized feed aggregation,
vehicle detection, plate recognition, durable observations, representative watchlist
matching, alerts and vehicle history. Existing departmental recordings are retained.
The app runs locally on the RTX 3050. Paid hosting is not required for the saved
submission guide; a hosted platform link is optional.

The final upgrade passes 62 backend tests, the frontend build and browser checks.
It fixes retained image memory, bounds OCR state, prevents confidence from crossing
between plate strings, isolates camera resets, keeps diagnostic work off the API
request loop, and restores visible reconnect controls after a loaded video stops.
Public code: https://github.com/MO-ALAIN/sentinel-cctv . Original private Git history,
credentials, databases, government imagery and source videos are excluded.

## Documents and demonstration requirements

| Required item | Prepared artifact | Final action |
|---|---|---|
| Solution presentation, PPT/PDF | Eight-slide SOLUTION_PRESENTATION.pdf | Upload and verify viewer access |
| Technical proposal / HLD | HIGH_LEVEL_DESIGN.pdf, with architecture and 80,000-camera sizing assumptions | Upload and verify viewer access |
| Own-source screen recording, maximum 2–3 minutes | Real licensed Finnish footage through onboarding, recognition, a representative watchlist, new automatic alert, evidence and history export | Use the final validated take in the submission folder |
| Government-source screen recording | Actual organizer feed, catalogue import, viewing and available analytics | Use the final validated take in the submission folder |
| Government analytics output with timestamps | CSV plus a report describing its camera, observation window, source-time basis and sampling limits | Upload with the government video |
| Reviewer-accessible links | GitHub source is public; local documents/videos are prepared | Upload videos to unlisted YouTube or Drive/OneDrive with Anyone-with-link Viewer access |
| Team/portal fields and submission receipt | Not verified or submitted | Confirm registration/category, exact closing time and required portal fields before submission |

## Seven evaluation areas and honest limits

| Area | What the build demonstrates | Remaining evidence gap |
|---|---|---|
| Successful test case | Organizer ingestion, viewing, detection and timestamped output; foreign plate recognition and alert workflow | Designated Indian vehicle recognition on organizer cameras remains unverified |
| Solution presentation | Model choice, workflow, technology, benefits and constraints | Review final file and link access |
| Architecture | Direct source ingestion, local persistence, event flow, regional scaling formulas and department prerequisites | Vendor-specific feasibility data and actual infrastructure quotations |
| Working platform | Real backend and browser demonstrations; 62 backend tests | This is a local proof of concept, not production certification |
| Video analytics output | Two complete foreign regression scenes each yield 4 correct appearances, 0 false and 0 missed | Same four vehicles in reused Finnish scenes; not Indian/general accuracy |
| Scalability and PoC readiness | Two-worker admission, responsive controls, restart preservation, bounded OCR state; regional/edge plan | Long-duration sustainable throughput, 50-camera evaluation load and 80,000-camera rollout are not demonstrated |
| Submission completeness | Presentation, HLD, videos, reports, metadata export, API contract and source | External viewer links, portal fields and actual submission remain |

## Model-specific prerequisites

- Model 1 registry, manual/CSV/API onboarding, filters, audit, metadata gap reporting
  and surveyed polygon gap calculations are implemented. Organizer camera coordinates
  and verified survey boundaries are missing, so actual geographic coverage cannot
  be measured. The sample registry and gap reports retain those unknowns.
- Model 2 can consume RTSP/HTTP and authorized local recordings. One organizer gateway
  and public recordings have been demonstrated. Two camera IDs, two files, or two
  vendor labels do not prove integration with two independent departmental VMS systems.
- Stored cross-camera plate observations are searchable. Original capture times and
  locations of the public scenes are not verified, so they do not establish a real
  geographic journey. Watchlist source labels do not imply access to VAHAN/CCTNS or
  another external database.
- FRS, vendor federation and centralized full recording were not selected. Proposed
  additions in the HLD are clearly separated from deployed features.

## Source and deadline verification

Requirements were checked against the complete official pages saved on 5–6 September
under `E:/gujarat police/project-review`, especially the problem statement's submission
section. New home/problems/FAQ requests failed again on 14 September. The working
submission date is 15 September 2026 from the user and saved site; its exact closing
hour and any portal updates must be verified when logged in. No numeric scoring
weights or shortlist guarantee are assumed.

No competition submission or video/document upload has been made. The local package
is `E:/gujarat police/submission-20260914`. Its START-HERE file and validation manifest
identify the selected files; failed and earlier demo takes remain outside the package.
