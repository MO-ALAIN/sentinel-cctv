"""
Sighting persistence layer — the spine that makes cross-camera vehicle tracing possible.

WHY THIS EXISTS (read before editing):
    ANPR plate reads used to live only in ANPRManager._anpr_records, an in-memory
    dict that is wiped on every restart and only knows about currently-running
    streams. The graded hackathon test case ("given a plate, trace it across the
    network with timestamped route history") is impossible against volatile memory.
    This module writes every confirmed plate read to SQLite as a durable "sighting",
    so a plate seen on cam04 at 10:00 and cam17 at 10:12 becomes a queryable route.

THREADING NOTE:
    ANPRManager.process_vehicle_crop() runs inside stream-worker THREADS, not the
    FastAPI async event loop. So this repository is deliberately SYNCHRONOUS and
    thread-safe: one shared sqlite3 connection (check_same_thread=False) guarded by a
    single RLock, in WAL mode so the async API can read while workers write. It does
    NOT use the app's async SQLAlchemy engine (that would require awaiting from a
    non-async thread). See CONTRACT.md §2 for the schema this owns.
"""
import sqlite3
import threading
import logging
import re
from app.paths import DB_PATH
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# CWD-relative, IDENTICAL to the async engine's DATABASE_URL
# ("sqlite+aiosqlite:///./cctv_surveillance.db") so both engines point at the SAME
# physical file regardless of which one touches it.
DB_FILENAME = str(DB_PATH)


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_plate(text: Optional[str]) -> str:
    """Uppercase, then keep only alphanumerics. Must match the frontend + ANPR cleaner.
    'gj-01 ab 1234' -> 'GJ01AB1234'."""
    if not text:
        return ""
    return re.sub(r'[^A-Z0-9]', '', text.upper())


class SightingRepository:
    def __init__(self, db_filename: str = DB_FILENAME):
        self._db_filename = db_filename
        self._lock = threading.RLock()
        self._conn: Optional[sqlite3.Connection] = None

    # ---------- connection / schema ----------
    def _connect(self) -> sqlite3.Connection:
        if self._conn is None:
            conn = sqlite3.connect(self._db_filename, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA journal_mode=WAL;")
            conn.execute("PRAGMA synchronous=NORMAL;")
            self._conn = conn
            self._ensure_schema(conn)
            logger.info(f"SightingRepository connected to {self._db_filename} (WAL mode).")
        return self._conn

    def _ensure_schema(self, conn: sqlite3.Connection) -> None:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS cameras (
                id          TEXT PRIMARY KEY,
                name        TEXT,
                location    TEXT,
                district    TEXT,
                department  TEXT,
                lat         REAL,
                lon         REAL,
                rtsp_url    TEXT,
                anpr_status TEXT DEFAULT 'UNKNOWN',
                status      TEXT DEFAULT 'AVAILABLE',
                updated_at  TEXT
            );

            CREATE TABLE IF NOT EXISTS plate_sightings (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                camera_id    TEXT NOT NULL,
                track_id     INTEGER,
                vehicle_type TEXT,
                status       TEXT,
                confidence   REAL,
                lat          REAL,
                lon          REAL,
                location     TEXT,
                crop_path    TEXT,
                sighted_at   TEXT NOT NULL,
                created_at   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_sightings_plate ON plate_sightings(plate_number);
            CREATE INDEX IF NOT EXISTS idx_sightings_time  ON plate_sightings(sighted_at);

            CREATE TABLE IF NOT EXISTS watchlist (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL UNIQUE,
                reason       TEXT DEFAULT 'BOLO',
                severity     TEXT DEFAULT 'MEDIUM',
                description  TEXT,
                source       TEXT DEFAULT 'MANUAL',
                active       INTEGER DEFAULT 1,
                created_at   TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS alerts (
                id           INTEGER PRIMARY KEY AUTOINCREMENT,
                plate_number TEXT NOT NULL,
                watchlist_id INTEGER,
                sighting_id  INTEGER,
                camera_id    TEXT,
                reason       TEXT,
                severity     TEXT,
                lat          REAL,
                lon          REAL,
                location     TEXT,
                message      TEXT,
                acknowledged INTEGER DEFAULT 0,
                created_at   TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_alerts_ack ON alerts(acknowledged);
            """
        )
        extras = {
            'cameras': {'source_type': "TEXT DEFAULT 'LIVE'", 'source_system': 'TEXT',
                        'camera_type': "TEXT DEFAULT 'IP'", 'ownership': 'TEXT', 'storage_details': 'TEXT',
                        'retention_days': 'INTEGER', 'maintenance_status': "TEXT DEFAULT 'UNKNOWN'",
                        'geo_source': "TEXT DEFAULT 'UNKNOWN'", 'recording_started_at': 'TEXT',
                        'stream_codec':'TEXT','stream_width':'INTEGER','stream_height':'INTEGER',
                        'declared_fps':'REAL','catalogue_live':'INTEGER','desired_connected':'INTEGER DEFAULT 0'},
            'plate_sightings': {'source_type': "TEXT DEFAULT 'UNKNOWN'", 'session_id': 'TEXT',
                               'media_offset_seconds': 'REAL', 'timestamp_basis': "TEXT DEFAULT 'PROCESSING_TIME'",
                               'geo_source': "TEXT DEFAULT 'UNKNOWN'"}
        }
        for table, fields in extras.items():
            columns = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
            for name, definition in fields.items():
                if name not in columns:
                    conn.execute(f'ALTER TABLE {table} ADD COLUMN {name} {definition}')
        conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_session_track ON plate_sightings(camera_id,session_id,track_id) WHERE session_id IS NOT NULL AND track_id IS NOT NULL')
        conn.execute('CREATE TABLE IF NOT EXISTS audit_log(id INTEGER PRIMARY KEY, actor TEXT, action TEXT, target TEXT, created_at TEXT)')
        conn.execute('CREATE TABLE IF NOT EXISTS coverage_layers(id TEXT PRIMARY KEY, feature_json TEXT NOT NULL)')
        conn.commit()

    def close(self):
        with self._lock:
            if self._conn:
                self._conn.close()
                self._conn = None

    def audit(self, actor, action, target):
        with self._lock, self._connect() as conn:
            conn.execute('INSERT INTO audit_log(actor,action,target,created_at) VALUES(?,?,?,?)', (actor, action, str(target), _now_iso()))

    def audit_history(self):
        with self._lock:
            return [dict(r) for r in self._connect().execute('SELECT * FROM audit_log ORDER BY id DESC LIMIT 200')]

    def set_connection_intent(self, camera_id, connected, actor='operator'):
        with self._lock, self._connect() as conn:
            conn.execute('UPDATE cameras SET desired_connected=? WHERE id=?',(int(connected),camera_id))
            conn.execute('INSERT INTO audit_log(actor,action,target,created_at) VALUES(?,?,?,?)',
                         (actor,'CAMERA_CONNECT' if connected else 'CAMERA_DISCONNECT',camera_id,_now_iso()))

    def save_cameras(self, cameras, actor='system'):
        with self._lock, self._connect() as conn:
            allowed = {r[1] for r in conn.execute('PRAGMA table_info(cameras)')}
            for cam in cameras:
                values = {k:v for k,v in cam.items() if k in allowed}
                values['updated_at'] = _now_iso()
                keys = list(values)
                updates = ','.join(f'{k}=excluded.{k}' for k in keys if k != 'id')
                conn.execute(f"INSERT INTO cameras ({','.join(keys)}) VALUES ({','.join('?' for _ in keys)}) ON CONFLICT(id) DO UPDATE SET {updates}", list(values.values()))
                conn.execute('INSERT INTO audit_log(actor,action,target,created_at) VALUES(?,?,?,?)', (actor, 'CAMERA_UPSERT', cam['id'], _now_iso()))

    # ---------- cameras / registry (Model 1 foundation) ----------
    def upsert_camera(self, cam: Dict[str, Any]) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                """
                INSERT INTO cameras (id, name, location, district, department, lat, lon,
                                     rtsp_url, anpr_status, status, updated_at)
                VALUES (:id, :name, :location, :district, :department, :lat, :lon,
                        :rtsp_url, :anpr_status, :status, :updated_at)
                ON CONFLICT(id) DO UPDATE SET
                    name=excluded.name, location=excluded.location, district=excluded.district,
                    department=excluded.department, lat=excluded.lat, lon=excluded.lon,
                    rtsp_url=excluded.rtsp_url,
                    anpr_status=COALESCE(excluded.anpr_status, cameras.anpr_status),
                    status=excluded.status, updated_at=excluded.updated_at
                """,
                {
                    "id": cam["id"],
                    "name": cam.get("name"),
                    "location": cam.get("location"),
                    "district": cam.get("district"),
                    "department": cam.get("department"),
                    "lat": cam.get("lat"),
                    "lon": cam.get("lon"),
                    "rtsp_url": cam.get("rtsp_url"),
                    "anpr_status": cam.get("anpr_status"),  # None => keep existing (COALESCE)
                    "status": cam.get("status", "AVAILABLE"),
                    "updated_at": _now_iso(),
                },
            )
            conn.commit()

    def list_cameras(self) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            rows = conn.execute("SELECT * FROM cameras ORDER BY id").fetchall()
            return [dict(r) for r in rows]

    def get_camera(self, camera_id: str) -> Optional[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            row = conn.execute("SELECT * FROM cameras WHERE id=?", (camera_id,)).fetchone()
            return dict(row) if row else None

    def set_camera_anpr_status(self, camera_id: str, anpr_status: str) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute(
                "UPDATE cameras SET anpr_status=?, updated_at=? WHERE id=?",
                (anpr_status, _now_iso(), camera_id),
            )
            conn.commit()

    # ---------- sightings (HOT PATH — called from ANPR worker threads) ----------
    def record_sighting(
        self,
        *,
        plate_number: str,
        camera_id: str,
        track_id: Optional[int] = None,
        vehicle_type: Optional[str] = None,
        status: Optional[str] = None,
        confidence: Optional[float] = None,
        sighted_at: Optional[str] = None,
        crop_path: Optional[str] = None,
        session_id: Optional[str] = None,
        source_type: Optional[str] = None,
        media_offset_seconds: Optional[float] = None,
        timestamp_basis: str = 'PROCESSING_TIME',
    ) -> Dict[str, Any]:
        """Persist one sighting and, if the plate is on the active watchlist, raise an alert.
        Returns {sighting_id, plate_number, alert}. `alert` is None when no watchlist hit."""
        norm = normalize_plate(plate_number)
        if not norm:
            return {}
        sighted_at = canonical_time(sighted_at) if sighted_at else _now_iso()
        with self._lock, self._connect() as conn:
            if session_id and track_id is not None:
                previous = conn.execute('SELECT id FROM plate_sightings WHERE camera_id=? AND session_id=? AND track_id=?', (camera_id,session_id,track_id)).fetchone()
                if previous:
                    return {'sighting_id': previous['id'], 'plate_number': norm, 'alert': None, 'duplicate': True}
            cam = conn.execute(
                "SELECT * FROM cameras WHERE id=?", (camera_id,)
            ).fetchone()
            if not cam:
                raise ValueError('Onboard the camera before recording sightings')
            lat = cam["lat"] if cam else None
            lon = cam["lon"] if cam else None
            location = cam["location"] if cam else None
            cur = conn.execute(
                """INSERT INTO plate_sightings
                   (plate_number, camera_id, track_id, vehicle_type, status, confidence,
                    lat, lon, location, crop_path, sighted_at, created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
                (norm, camera_id, track_id, vehicle_type, status, confidence,
                 lat, lon, location, crop_path, sighted_at, _now_iso()),
            )
            sighting_id = cur.lastrowid
            conn.execute('UPDATE plate_sightings SET session_id=?,source_type=?,media_offset_seconds=?,timestamp_basis=?,geo_source=? WHERE id=?',
                         (session_id,source_type or cam['source_type'],media_offset_seconds,timestamp_basis,cam['geo_source'],sighting_id))
            alert = self._match_and_alert(conn, norm, sighting_id, camera_id, lat, lon, location) if status == 'CONFIRMED' else None
        return {"sighting_id": sighting_id, "plate_number": norm, "alert": alert}

    def _match_and_alert(self, conn, norm_plate, sighting_id, camera_id, lat, lon, location):
        wl = conn.execute(
            "SELECT * FROM watchlist WHERE plate_number=? AND active=1", (norm_plate,)
        ).fetchone()
        if not wl:
            return None
        # Keep every sighting, but do not flood the operator when a track splits.
        # Media-time comparison stays within one camera/session; replays and
        # appearances on other cameras remain separately alertable.
        sighting = conn.execute('SELECT session_id,media_offset_seconds FROM plate_sightings WHERE id=?',(sighting_id,)).fetchone()
        if sighting['session_id'] and sighting['media_offset_seconds'] is not None:
            recent = conn.execute(
                "SELECT a.id FROM alerts a JOIN plate_sightings s ON s.id=a.sighting_id "
                "WHERE a.camera_id=? AND a.watchlist_id=? AND s.session_id=? "
                "AND s.media_offset_seconds BETWEEN ? AND ? LIMIT 1",
                (camera_id,wl['id'],sighting['session_id'],sighting['media_offset_seconds']-2.0,sighting['media_offset_seconds'])
            ).fetchone()
            if recent:
                return None
        message = f"WATCHLIST HIT: {norm_plate} ({wl['reason']}) seen at {location or camera_id}"
        cur = conn.execute(
            """INSERT INTO alerts
               (plate_number, watchlist_id, sighting_id, camera_id, reason, severity,
                lat, lon, location, message, acknowledged, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?,0,?)""",
            (norm_plate, wl["id"], sighting_id, camera_id, wl["reason"], wl["severity"],
             lat, lon, location, message, _now_iso()),
        )
        logger.warning(message)
        return {
            "alert_id": cur.lastrowid,
            "reason": wl["reason"],
            "severity": wl["severity"],
            "message": message,
        }

    def trace_plate(self, plate_number: str, from_time=None, to_time=None, source_type=None) -> Dict[str, Any]:
        """THE graded test case: full timestamped route for a plate across all cameras."""
        norm = normalize_plate(plate_number)
        with self._lock:
            conn = self._connect()
            rows = conn.execute(
                "SELECT * FROM plate_sightings WHERE plate_number=? ORDER BY sighted_at ASC",
                (norm,),
            ).fetchall()
            route = [dict(r) for r in rows]
            if from_time:
                route = [r for r in route if r['sighted_at'] >= canonical_time(from_time)]
            if to_time:
                route = [r for r in route if r['sighted_at'] <= canonical_time(to_time)]
            if source_type:
                route = [r for r in route if r['source_type'] == source_type]
            wl = conn.execute(
                "SELECT * FROM watchlist WHERE plate_number=? AND active=1", (norm,)
            ).fetchone()
        return {
            "plate_number": norm,
            "total_sightings": len(route),
            "first_seen": route[0]["sighted_at"] if route else None,
            "last_seen": route[-1]["sighted_at"] if route else None,
            "distinct_cameras": len({r["camera_id"] for r in route}),
            "on_watchlist": bool(wl),
            "watchlist": (dict(wl) if wl else None),
            "route": route,
        }

    def list_sightings(self, plate: Optional[str] = None, camera_id: Optional[str] = None,
                       limit: int = 200) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            q = "SELECT * FROM plate_sightings"
            clauses, params = [], []
            if plate:
                clauses.append("plate_number=?")
                params.append(normalize_plate(plate))
            if camera_id:
                clauses.append("camera_id=?")
                params.append(camera_id)
            if clauses:
                q += " WHERE " + " AND ".join(clauses)
            q += " ORDER BY sighted_at DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(q, params).fetchall()]

    # ---------- watchlist ----------
    def get_sighting(self, sighting_id):
        with self._lock:
            row = self._connect().execute('SELECT * FROM plate_sightings WHERE id=?', (sighting_id,)).fetchone()
            return dict(row) if row else None

    def add_watchlist(self, *, plate_number: str, reason: str = "BOLO", severity: str = "MEDIUM",
                      description: Optional[str] = None, source: str = "MANUAL") -> Dict[str, Any]:
        norm = normalize_plate(plate_number)
        if not norm:
            raise ValueError("plate_number required")
        with self._lock:
            conn = self._connect()
            conn.execute(
                """INSERT INTO watchlist (plate_number, reason, severity, description, source, active, created_at)
                   VALUES (?,?,?,?,?,1,?)
                   ON CONFLICT(plate_number) DO UPDATE SET
                     reason=excluded.reason, severity=excluded.severity,
                     description=excluded.description, source=excluded.source, active=1""",
                (norm, reason, severity, description, source, _now_iso()),
            )
            conn.commit()
            row = conn.execute("SELECT * FROM watchlist WHERE plate_number=?", (norm,)).fetchone()
            return dict(row)

    def list_watchlist(self, active_only: bool = True) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            q = "SELECT * FROM watchlist"
            if active_only:
                q += " WHERE active=1"
            q += " ORDER BY created_at DESC"
            return [dict(r) for r in conn.execute(q).fetchall()]

    def delete_watchlist(self, wl_id: int) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("UPDATE watchlist SET active=0 WHERE id=?", (wl_id,))
            conn.commit()

    def match_watchlist(self, plate_number: str) -> Optional[Dict[str, Any]]:
        norm = normalize_plate(plate_number)
        with self._lock:
            conn = self._connect()
            row = conn.execute(
                "SELECT * FROM watchlist WHERE plate_number=? AND active=1", (norm,)
            ).fetchone()
            return dict(row) if row else None

    # ---------- alerts ----------
    def list_alerts(self, acknowledged: Optional[bool] = None, limit: int = 100) -> List[Dict[str, Any]]:
        with self._lock:
            conn = self._connect()
            q = "SELECT a.*, s.source_type, s.sighted_at, s.geo_source FROM alerts a LEFT JOIN plate_sightings s ON s.id=a.sighting_id"
            params: List[Any] = []
            if acknowledged is not None:
                q += " WHERE acknowledged=?"
                params.append(1 if acknowledged else 0)
            q += " ORDER BY a.created_at DESC LIMIT ?"
            params.append(limit)
            return [dict(r) for r in conn.execute(q, params).fetchall()]

    def acknowledge_alert(self, alert_id: int) -> None:
        with self._lock:
            conn = self._connect()
            conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))
            conn.commit()

    # ---------- dashboard stats ----------
    def stats(self) -> Dict[str, Any]:
        with self._lock:
            conn = self._connect()

            def scalar(q: str) -> int:
                return conn.execute(q).fetchone()[0]

            return {
                "total_sightings": scalar("SELECT COUNT(*) FROM plate_sightings"),
                "distinct_plates": scalar("SELECT COUNT(DISTINCT plate_number) FROM plate_sightings"),
                "cameras_registered": scalar("SELECT COUNT(*) FROM cameras"),
                "cameras_with_geo": scalar("SELECT COUNT(*) FROM cameras WHERE lat IS NOT NULL"),
                "watchlist_active": scalar("SELECT COUNT(*) FROM watchlist WHERE active=1"),
                "alerts_open": scalar("SELECT COUNT(*) FROM alerts WHERE acknowledged=0"),
            }


# Global singleton (import this everywhere: `from app.services.sighting_repository import sighting_repo`)
sighting_repo = SightingRepository()

def canonical_time(value):
    dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    if dt.tzinfo is None:
        raise ValueError('Timestamp must include a timezone')
    return dt.astimezone(timezone.utc).isoformat()
