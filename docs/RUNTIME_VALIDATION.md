# Runtime and recovery validation — 13 September 2026

The local RTX 3050 release has a configurable admission limit for unified camera
workers, default two. This bounds concurrent decoders/analytics; it does not certify
that two arbitrary feeds run in real time. Registry size is independent of this
worker limit. Increase MAX_ACTIVE_CAMERAS only after measuring the target machine.

## Measured mixed-source run

One authorized organizer replay (cam06) and one licensed recorded source
(PUBLIC-CARPARK) ran together during a 60-second observation. An attempted third
camera returned HTTP 409 with a readable disconnect-first message; its saved
connection intent was unchanged. The completed recording released its slot.

| Measure | Observed result |
|---|---:|
| Runtime samples | 51 |
| Sampled system-health API errors | 0 |
| Median / maximum sampled health latency | 6.63 / 452.82 ms |
| Maximum concurrent unified workers | 2 |
| Peak combined preview-process RSS | 1,516.25 MiB |
| Recorded source | All 600 frames decoded; ENDED |
| New recorded-source plate observations | 4, matching the four known registrations |
| Organizer report | 2 sampled detection events, 2 session-local tracks, 0 confirmed plates |
| Organizer streaming health samples | 59 / 59 |

These are local observations from one short run, not a load-test certification,
real-time source throughput, unique-vehicle truth, Indian ANPR accuracy or proof of
two departmental VMS integrations. The foreign clip is a reused regression sample.
The reporting buffer did not saturate. GPU counters are saved in the private raw
report as whole-device samples; they are not a per-process VRAM capacity estimate.
Timing includes the source, models and machine state during this run. There was no
controlled CPU/GPU baseline or repeated statistical performance trial.

## Recovery and controls

An actual preview-process restart preserved all 40 existing sightings, 2 watchlist
entries and 19 alert rows, including acknowledgement state, compared field-for-field
by ID. The selected organizer network source resumed decoding automatically.
The recorded source did not auto-replay. This is one recovery check, not a long
soak test or a high-availability guarantee.

Concurrent-request tests enforce the limit atomically, count reconnecting workers,
allow an existing feed to be reused, release ended recordings and prevent failed
starts from leaking a slot. Excess saved startup intents are skipped with a log
entry instead of failing startup. Users can connect them after freeing a slot.

Stalled workers remain disconnectable from Live Cameras, Camera Management and the
camera detail view. They retain their actual ERROR/RECONNECTING status. System
Status shows worker usage. Browser tests cover simulated stalled-source and limit
errors separately from the real admission/recovery checks above.

Validation: 46 backend tests, production frontend build, actual two-scene history
browser check, simulated failure-control browser check. Private evidence:
`docs/verification/runtime-two-sources-sept13.json`, `restart-recovery-sept13.json`,
`capacity-browser-sept13.json`, and `data/government-ocr-sept13/cam06-capacity.*`.
The runtime probe is a private measurement helper, not a shipped load generator.

Still open: representative Indian plate footage, genuinely independent source
systems, longer sustained-load/reconnect testing and verified source time/location.
Final matched video/report captures and presentation/HLD revision remain scheduled
for 14 September. No cloud hosting has been activated.


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
