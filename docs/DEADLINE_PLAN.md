# Submission work plan: 12–15 September 2026 (IST)

Working deadline: 15 September, as stated by the user and the saved official guide.
The live site is currently unreachable from this environment; its exact closing
time is unverified. Internal target: submission package ready by 14 September
18:00 IST; submission/access checks by 15 September 12:00 IST, or earlier if the
portal's actual closing time requires it. Do not assume an end-of-day deadline.

| Date | Main work | Exit condition |
|---|---|---|
| 12 September | Recognition bottlenecks, plate-specific OCR comparison, real-source inspection, source/vehicle association correctness | Reproducible before/after diagnostic results; untouched validation source; false matches retained in reports |
| 13 September | Integrate only measured improvements; verify cross-camera metadata/alerts, two source systems where access exists, bounded concurrency and restart recovery | Tested release, repeatable operator workflow and honest capacity/accuracy measurements; feature freeze by 18:00 |
| 14 September | Record final own-source and government-source demos; produce matching timestamped output report; finalize PPT/PDF and HLD | Consistent package by 18:00; videos and metrics correspond to the frozen version; prepare permitted reviewer links |
| 15 September | Check registration/team fields, exact portal deadline, links outside owner account, report/video/document consistency; submit with required access | Submission receipt saved; reserve time for upload/access failures; only critical fixes |

The existing presentation and HLD are drafts, so their final revision can wait
until the measurements stabilize. Capture evidence as code changes; do not leave
all recording and documentation until deadline day. If a new model fails validation,
keep the proven baseline and disclose its limits instead of rushing an untested swap.

## Priorities tied to official evaluation

1. Government-feed onboarding, actual viewing and timestamped analytics output.
2. Reliable recognition: exact-match precision/recall, misses, false alerts, independent source frames.
3. Working own-source watchlist → automatic alert → evidence → vehicle-history workflow.
4. Model 1 + Model 2 interoperability and truthful location/source metadata.
5. Complete-pipeline resource use, recovery, bounded workload and credible 80,000-camera architecture.
6. Clear presentation/HLD and complete, accessible submission materials.

No paid cloud deployment or cosmetic feature expansion is planned. The full app
runs locally on the RTX 3050; GitHub is used for source collaboration. Two labels
for the same feed do not prove two VMS integrations, and replayed copies do not
prove a real cross-camera vehicle journey. Missing real evidence stays explicit.

## External inputs that affect acceptance

- Organizer access and genuinely different source systems; verified camera location/department metadata.
- Readable Indian plates and the designated registration supplied for on-site evaluation.
- Team registration details and portal upload access, plus an authorized video-link destination.

Current evidence and limitations: CURRENT_STATUS.md and SUBMISSION_READINESS.md.
This is a work schedule, not an unattended recurring job. Continue from the highest
unfinished acceptance condition whenever work resumes.
