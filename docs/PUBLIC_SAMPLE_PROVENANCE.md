# Public-source demonstration provenance

The user authorized sourcing real public footage when no own camera/video was available. These clips are dataset-author originals, not someone else's annotated model results. They are stored under `scratch/public-uvg/` and excluded from source control.

Source: [UVG-VCM, Tampere University](https://tie-ultravideo.rd.tuni.fi/UVG-VCM/index.html). License: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution: T. Partanen, M. Anttila, R. Kortelahti, G. Gautier, A. Mercat and J. Vanne, “UVG-VCM: Benchmarking dataset for machine-oriented visual data compression,” QoMEX 2026. The publisher states visible plates have publication/research permission. Source page copy is retained privately in `data/public-source-review/uvg-vcm.html`.

| File | Original download | SHA-256 |
|---|---|---|
| CarPark.mp4 | [Car Park](https://tie-ultravideo.rd.tuni.fi/UVG-VCM/CarPark/CarPark.mp4), 73,625,481 bytes, 600 frames, 60 fps | `5022723acac30a3734b559ac02d36a9a13d43f88ba4b0991d8deb6e893b0a41f` |
| ParkingGarage.mp4 | [Parking Garage](https://tie-ultravideo.rd.tuni.fi/UVG-VCM/ParkingGarage/ParkingGarage.mp4), 120,830,457 bytes, 1,140 frames, 60 fps | `aabbde5730f95eb6fb681e79da9a4ea544a62e6155e1219514909b60c7451403` |

Both recordings were onboarded and fully processed. Parking Garage was independently compared on 12 September; see OCR_VALIDATION.md. Screen recordings add our application's detection overlays and interface; source video pixels were not edited or synthesized. The public sample is Finnish, not Indian or organizer footage. It proves a real pipeline demonstration only; it does not prove Indian accuracy, multi-vendor integration or an actual multi-camera journey.

Camera `PUBLIC-CARPARK` is explicitly named as a public Finland sample and labelled RECORDED. `ANPR_CAMERA_FORMATS` permits FINLAND_STANDARD only on named configured cameras; all organizer cameras keep INDIA validation. The limited car/trailer grammar follows [Traficom's format description](https://traficom.fi/en/drivers-and-vehicles/vehicle-registration/order-vehicle-registration-plate-inspection-station). It does not implement every Finnish plate type or use expected plate text to guide OCR.

The representative watchlist record is labelled PUBLIC_SAMPLE_TEST and explicitly says the vehicle is not a suspect or stolen vehicle. Matching alerts are demonstration records, not findings about the owner. Existing records from repeated test runs remain retained and distinguishable by session/media offset; they must not be described as separate real journeys.

## Independent comparison

[Author annotations](https://tie-ultravideo.rd.tuni.fi/UVG-VCM/CarPark/CarPark_annotations.json) were retrieved after the initial recognition run. The full ten-second clip contains four full labelled registrations: ZPN720, HTI748, MLZ106 and BSA788. Partial strings as cars leave the frame are excluded; continuous appearances under changing annotation IDs are merged. Frame 1 maps to media offset 0 at 60 fps. The label manifest records source/annotation hashes and this policy.

Initial results: two correct appearances, a duplicate ZPN720, an incorrect HT748 and two missed appearances. Event precision/recall are both 50%; the duplicate counts as a false positive under the documented evaluator. This is a four-appearance diagnostic sample, not an independent held-out benchmark after tuning. Updated results are recorded separately in `verification/public-source-evaluation-refined.json`.

Actual-crop OCR comparison found `HT| 748` and `HT.748`; silently deleting the ambiguous stroke produced a different valid-looking plate. The validator now rejects embedded unsupported punctuation, while allowing whitespace/hyphens and harmless edge punctuation. This rejects uncertainty instead of guessing a replacement character. A two-second media-time alert cooldown suppresses immediate repeats within the same camera/session/watchlist entry; it retains all sightings, so duplicate observations are still penalized by evaluation. Other cameras, replay sessions and later appearances remain alertable.


ParkingGarage author annotations were retrieved on 12 September from
https://tie-ultravideo.rd.tuni.fi/UVG-VCM/ParkingGarage/ParkingGarage_annotations.json .
SHA-256: `d36254b2fb98e3dbea2cbde411452b67b0c5259b56dc84522c3499b541a947f4`.
The file's `version` key is metadata, not a frame. Numeric frame keys contain
four complete plate appearances; empty texts are not ground truth. Reference
intervals, file hashes and scoring policy are in `verification/garage-reference-labels.json`.
Camera PUBLIC-GARAGE uses RECORDED/FINLAND_STANDARD and no invented coordinates or
original UTC recording time. Matching plates across these real scenes establish
recorded cross-camera recognition, not original movement timing or vendor federation.
