# FROZEN INTERFACE CONTRACT — v1

## Implementation extension — 5 September 2026

The user authorized completion across backend, frontend and documentation. Existing
endpoint names and JSON keys below remain stable. These additive changes are agreed
for the complete Model 1 + Model 2 implementation:

- `POST /api/registry/cameras` validates and upserts a camera; `POST /api/registry/import`
  accepts `{csv: string}` and validates every row before any writes.
- `GET /api/registry/export` returns CSV; `GET /api/registry/gaps` returns metadata,
  coordinate, health and maintenance gaps (not a claim of geographic coverage).
- Camera fields add `source_type` (LIVE, GOVERNMENT_REPLAY, RECORDED), `source_system`,
  `camera_type`, `ownership`, `storage_details`, `retention_days`, `maintenance_status`,
  `geo_source` (VERIFIED, REPRESENTATIVE, UNKNOWN), and `recording_started_at`.
- `POST /api/watchlist/import` accepts CSV. Existing POST also updates by normalized plate.
- `GET /api/investigation/export` exports timestamped sightings with optional plate,
  camera, from/to time and source filters; trace accepts from/to and source filters.
- Sightings add source/session provenance, media offset, timestamp basis and geo source.
  Low-confidence observations remain searchable but never trigger a confirmed watchlist hit.
- `GET /api/investigation/evidence/{sighting_id}` serves only the associated image
  within the configured evidence directory. Crop filesystem paths are not public URLs.
- `GET /api/registry/audit` returns operator metadata/action audit history.
- `/api/auth/session`, `/api/auth/login`, `/api/auth/logout` manage same-origin sessions.
  Unconfigured authentication permits loopback-only development. Network deployment
  requires configured credentials. Admin can onboard/edit watchlists; operator can
  investigate/acknowledge; viewer can read. This initial deployment uses one shared
  department scope; federation-wide department isolation is a documented deployment gap.
- Public camera responses redact stream credentials. Registry-backed sources are available
  to the existing connect/disconnect endpoints; local recordings must be under MEDIA_DIR.
- The API stores UTC times and the interface formats them in Asia/Kolkata. Lines between
  camera sightings show observed order, not inferred road routes.


**Purpose:** This is the single source of truth that lets three builders (Claude Code on the repo, Codex on the frontend, Fable on the docs) work in parallel **without colliding**. Nobody invents their own schema or endpoint names. If something here must change, change it *here first*, announce it, then code.

> Read this once end-to-end. It is also the map of how the new "police" features connect to the existing traffic-analytics app.

---

## 1. Why these pieces exist (the gap we are closing)

The hackatthon's graded test case is: **"Given a vehicle registration number, trace it across the camera network with timestamped, location-wise route history, and cross-reference a watchlist with automated alerts on a GIS map."**

The existing app could not do this because every plate read lived only in `ANPRManager._anpr_records` — an **in-memory dict wiped on restart** that only knows about currently-running streams. You cannot trace a route through volatile memory.

The fix is a **durable sighting spine**:

```
YOLO+ByteTrack detects vehicle ─► ANPR reads plate ─► record_sighting() writes a ROW to SQLite
                                                             │
        (plate, camera, timestamp, lat, lon, confidence) ───┘
                                                             │
                          ┌──────────────────────────────────┼───────────────────────────┐
                          ▼                                   ▼                           ▼
              TRACE: all rows for a plate,        WATCHLIST MATCH on every write,   GIS MAP: cameras +
              ordered by time = the ROUTE         hit ─► raise ALERT                sighting pins by lat/lon
```

Four new tables, four new route groups. Everything else in the app is untouched.

---

## 2. Data model (SQLite — `cctv_surveillance.db`)

Owned & created by `backend/app/services/sighting_repository.py` (`CREATE TABLE IF NOT EXISTS`, so it is safe to run repeatedly). The existing `camera_logs` table is unchanged.

### `cameras` — the registry + GIS foundation (Model 1)
| column | type | notes |
|---|---|---|
| id | TEXT PK | e.g. `cam04` |
| name | TEXT | |
| location | TEXT | human label, e.g. `Vadodara` |
| district | TEXT | |
| department | TEXT | Home Department / GSRTC / Municipal / Health / Panchayat / RTO / Food & Civil Supplies |
| lat | REAL | decimal degrees (nullable until seeded) |
| lon | REAL | decimal degrees |
| rtsp_url | TEXT | |
| anpr_status | TEXT | `ANPR_READY` / `ANPR_POTENTIAL` / `ANPR_LIMITED` / `ANPR_UNSUITABLE` / `UNKNOWN` |
| status | TEXT | `AVAILABLE` / `ONLINE` / `OFFLINE` |
| updated_at | TEXT | ISO 8601 |

### `plate_sightings` — the spine (one row per vehicle appearance per camera)
| column | type | notes |
|---|---|---|
| id | INTEGER PK | autoincrement |
| plate_number | TEXT | **normalized** (uppercase, alphanumerics only, e.g. `GJ01AB1234`) |
| camera_id | TEXT | |
| track_id | INTEGER | ByteTrack id |
| vehicle_type | TEXT | car / motorcycle / bus / truck |
| status | TEXT | `CONFIRMED` / `LOW_CONFIDENCE` |
| confidence | REAL | composite score 0–1 |
| lat, lon | REAL | copied from the camera at write time (denormalized on purpose) |
| location | TEXT | copied from camera |
| crop_path | TEXT | evidence image path (nullable) |
| sighted_at | TEXT | ISO 8601 — the time the plate was confirmed |
| created_at | TEXT | ISO 8601 |

### `watchlist` — vehicles of interest (you supply representative data)
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| plate_number | TEXT UNIQUE | normalized |
| reason | TEXT | `STOLEN` / `WANTED` / `SUSPECT` / `MISSING` / `BOLO` |
| severity | TEXT | `HIGH` / `MEDIUM` / `LOW` |
| description | TEXT | free text |
| source | TEXT | `VAHAN` / `CCTNS` / `MANUAL` … (simulated integration point) |
| active | INTEGER | 1 = active, 0 = removed |
| created_at | TEXT | |

### `alerts` — raised automatically when a sighting matches an active watchlist plate
| column | type | notes |
|---|---|---|
| id | INTEGER PK | |
| plate_number | TEXT | |
| watchlist_id | INTEGER | → watchlist.id |
| sighting_id | INTEGER | → plate_sightings.id |
| camera_id | TEXT | |
| reason, severity | TEXT | copied from watchlist |
| lat, lon, location | REAL/TEXT | where it was seen |
| message | TEXT | pre-formatted human string |
| acknowledged | INTEGER | 0 = open, 1 = acknowledged |
| created_at | TEXT | |

---

## 3. HTTP API (frozen)

Base URL in dev: `http://localhost:8000`. All new endpoints are additive; existing endpoints unchanged.

### Registry & GIS — `/api/registry`
- `GET /api/registry/cameras` → `Camera[]` (full rows above). **Frontend map reads this.**
- `GET /api/registry/stats` → counts (see §4 `RegistryStats`).

### Investigation / Trace — `/api/investigation`
- `GET /api/investigation/trace/{plate_number}` → `TraceResult` (see §4). **This is the graded test case.**
- `GET /api/investigation/sightings?plate=&camera_id=&limit=` → `Sighting[]` (debug/support).

### Watchlist — `/api/watchlist`
- `GET /api/watchlist?active_only=true` → `WatchlistEntry[]`
- `POST /api/watchlist` body `WatchlistCreate` → created `WatchlistEntry`
- `DELETE /api/watchlist/{id}` → `{ "deleted": id }` (soft delete, sets active=0)

### Alerts — `/api/alerts`
- `GET /api/alerts?acknowledged=false&limit=100` → `Alert[]` (newest first)
- `POST /api/alerts/{id}/acknowledge` → `{ "acknowledged": id }`

---

## 4. JSON shapes (frozen — copy verbatim, do not rename keys)

```jsonc
// TraceResult  — GET /api/investigation/trace/{plate}
{
  "plate_number": "GJ01AB1234",
  "total_sightings": 3,
  "first_seen": "2026-09-05T10:00:12+00:00",
  "last_seen":  "2026-09-05T10:14:48+00:00",
  "distinct_cameras": 3,
  "on_watchlist": true,
  "watchlist": { "reason": "STOLEN", "severity": "HIGH", "description": "..." },  // or null
  "route": [                                   // ordered oldest → newest
    {
      "id": 12, "plate_number": "GJ01AB1234", "camera_id": "cam04",
      "track_id": 7, "vehicle_type": "car", "status": "CONFIRMED",
      "confidence": 0.82, "lat": 22.3072, "lon": 73.1812, "location": "Vadodara",
      "crop_path": "scratch/sightings/GJ01AB1234_cam04_7.jpg",
      "sighted_at": "2026-09-05T10:00:12+00:00", "created_at": "..."
    }
    // ...
  ]
}

// Camera — GET /api/registry/cameras[]
{ "id":"cam04","name":"Camera CAM04","location":"Vadodara","district":"Vadodara",
  "department":"Home Department","lat":22.3072,"lon":73.1812,
  "rtsp_url":"rtsp://.../cam04","anpr_status":"ANPR_POTENTIAL","status":"AVAILABLE","updated_at":"..." }

// WatchlistCreate — POST body
{ "plate_number":"GJ01AB1234","reason":"STOLEN","severity":"HIGH","description":"Reported stolen 2026-09-01","source":"VAHAN" }

// Alert — GET /api/alerts[]
{ "id":5,"plate_number":"GJ01AB1234","watchlist_id":1,"sighting_id":12,"camera_id":"cam04",
  "reason":"STOLEN","severity":"HIGH","lat":22.3072,"lon":73.1812,"location":"Vadodara",
  "message":"WATCHLIST HIT: GJ01AB1234 (STOLEN) seen at Vadodara","acknowledged":0,"created_at":"..." }

// RegistryStats — GET /api/registry/stats
{ "total_sightings":42,"distinct_plates":9,"cameras_registered":30,"cameras_with_geo":30,
  "watchlist_active":4,"alerts_open":3 }
```

**Plate normalization rule (must be identical everywhere):** uppercase, then remove every non-alphanumeric character. `gj-01 ab 1234` → `GJ01AB1234`. The frontend should normalize the search box the same way before display, but the API normalizes on its side regardless.

---

## 5. Division of work (who owns what)

| Builder | Owns | Reads this contract for |
|---|---|---|
| **Claude Code** (repo) | DB schema, `sighting_repository.py`, ANPR write hook, all `/api/registry|investigation|watchlist|alerts` routes, startup seeding | — (author) |
| **Codex** (frontend) | New React pages: **Vehicle Trace** (search plate → route list + map), **Watchlist** (CRUD table), **Live Alerts** panel, **GIS Map** page (Leaflet, pins from `/api/registry/cameras`) | §3, §4 — build against these exact URLs & JSON keys |
| **Fable** (docs) | Solution Presentation (PPT), High-Level Design doc, architecture narrative, scalability write-up | §1, §2, and the reference-model framing in the problem statement |
| **You** (human) | Real-ish camera lat/lon (seeded — verify), record 2–3 min demo video, build watchlist CSV, submit | — |

**Frontend rules:**
- API base from a single constant (e.g. `const API = 'http://localhost:8000'`). Don't hardcode per-call.
- Map library: **Leaflet** + OpenStreetMap tiles (no API key). Center on Gujarat (`[22.6, 71.6]`, zoom 7).
- Never rename a JSON key from §4. If you need a new field, request it here first.

---

## 6. Known tradeoffs (be honest about these in the docs)
- Sightings are recorded **once per (camera, track)** on first confirmation — one route node per camera pass, not per frame.
- The repository uses a synchronous SQLite connection (WAL mode, one lock) because ANPR runs in worker threads. Fine for hackathon scale; the scaling doc should describe the Postgres/Kafka path for 80k cameras.
- Historical seed examples above are not the current registry: startup seeding is disabled. The actual organizer catalogue contains 30 IDs/names without coordinates. Missing coordinates remain unknown. Synthetic browser/test coordinates exist only in isolated fixtures.

## 7. Implemented contract additions — 8 September 2026

The historical ownership table and example counts above are planning context, not present runtime status. Current requirements and evidence are in `docs/REQUIREMENTS_AND_EVIDENCE.md`.

- Camera metadata includes source type/system, camera type, owner, storage/retention, maintenance, coordinate provenance and optional recording UTC origin. Public responses redact source credentials. Operator connection intent persists as `desired_connected`; only explicitly connected network sources resume after restart.
- Sightings are deduplicated by `(camera_id, session_id, track_id)` after two independent qualified frame votes. Watchlist matching is transactional with the confirmed sighting. Partial reads do not become confirmed matches. Stream timing uses PTS; unknown source UTC origin is labelled `PTS_ESTIMATED_UTC`.
- `GET/POST /api/registry/coverage`: list/import GeoJSON FeatureCollection survey layers. Properties: id, name, kind AREA/CAMERA, provenance VERIFIED/REPRESENTATIVE, and camera_id for footprints. Valid nonempty Polygon/MultiPolygon geometry required. Imports are atomic and admin-only.
- `GET /api/registry/coverage/gaps`: verified area/footprint union, square metre totals, percentage and uncovered geometry. No verified boundary returns `MISSING_VERIFIED_AREA`. Representative layers never count toward measured coverage.
- `DELETE /api/registry/coverage/{id}`: admin-only audited removal; absent ID returns 404.
- `/api/system/health` exposes actual device/model/OCR readiness, including `ai.anpr.trained_plate_detector_ready`. Readiness is not recognition accuracy or continuous stream availability.

## September 11 evidence additions

GET /api/detections/export returns an audited CSV of recent active-camera detections (optional camera_id), at most 100 buffered rows per camera and 500 combined. It includes camera/source/session, media offset and timestamp basis, primary detector class/score and any heuristic reclassification. Unconfirmed plate text is blank. This is neither a complete recording nor an accuracy report.

ANPR_CAMERA_FORMATS is a server configuration mapping named cameras to INDIA or FINLAND_STANDARD; the default remains INDIA. Representative public samples are labelled RECORDED. An immediate same-camera/session/watchlist repeat within two media seconds preserves the sighting but does not create another notification. Camera health distinguishes ENDED, DISCONNECTED and FRAME_DELIVERY_ERROR.
