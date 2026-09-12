# Organizer source check — 12 September 2026

Authorized catalogue/RTSP access was used for bounded checks of 29 cameras. The
previously demonstrated cam06 was excluded from this new survey. Of these 29,
22 decoded at least one image and 21 had advancing media timestamps. Seven returned
no frames within the observation window; one returned only one corrupted frame.
This is a sequential availability sample, not simultaneous camera capacity or a
continuous-availability guarantee. Some decoded images were also visibly corrupted.

Most sampled road views were at night with distant vehicles, glare, occlusion or
compression damage. Several other views showed no useful moving vehicles. No
complete registration could be independently verified from the inspected stills.
Camera labels and date overlays are source content, not independently verified
location, original UTC time or proof of distinct VMS integration.

Two subsequent 45-second checks used the actual running app and selected plate OCR:

| Camera | Detection events | Session-local tracks | Streaming health samples | Confirmed plates |
|---|---:|---:|---:|---:|
| cam12, toll lane | 5 | 2 | 44/45 | 0 |
| cam15, junction | 13 | 3 | 34/45 | 0 |

Events are sampled detections, not distinct vehicles. Neither API buffer saturated
during these checks. Missing plates were retained as UNREADABLE, TOO_SMALL or no
candidate; no text was invented. Vehicle reports include source type, media offset,
estimated timestamp basis and session ID. Original capture time remains unverified.
These checks used the new OCR engine before the later cross-class NMS change.

Private local artifacts: `docs/verification/organizer-survey-sept12.json`,
`data/source-survey-sept12/`, `data/source-survey-sept12-remaining/`, and
`data/government-ocr-sept12/{cam12,cam15}.{json,csv}`. Media, credentials and reports
are excluded from the public source export. Existing cam06 demo/report evidence is
retained. The final government video and report must be captured together from the
frozen version; the saved official guide permits timestamped vehicles OR plates.
Readable Indian plate accuracy and two genuinely different source systems remain
open acceptance gaps.
