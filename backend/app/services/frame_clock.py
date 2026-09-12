"""Media timing independent of delivery bursts and advertised frame rate."""
import math
from datetime import datetime, timezone, timedelta


class FrameClock:
    def __init__(self, source_origin=None):
        self.source_origin = datetime.fromisoformat(source_origin) if source_origin else None
        self.anchor = None
        self.previous_pts = None

    def observe(self, pts_ms, arrival=None):
        if not math.isfinite(pts_ms) or pts_ms < 0:
            return None
        pts = pts_ms / 1000.0
        if self.previous_pts is not None and abs(pts-self.previous_pts) < .000001:
            return None  # A duplicate PTS cannot count as an independent OCR frame.
        discontinuity = self.previous_pts is not None and pts < self.previous_pts
        if self.anchor is None or discontinuity:
            self.anchor = (arrival or datetime.now(timezone.utc)) - timedelta(seconds=pts)
        delta = 0 if self.previous_pts is None or discontinuity else pts-self.previous_pts
        self.previous_pts = pts
        origin = self.source_origin or self.anchor
        return {'pts_seconds': pts, 'delta_seconds': delta, 'discontinuity': discontinuity,
                'timestamp': (origin+timedelta(seconds=pts)).isoformat(),
                'timestamp_basis': 'SOURCE_TIME' if self.source_origin else 'PTS_ESTIMATED_UTC'}


class SceneBoundary:
    """Conservative hard-cut signal; thresholds require validation on organizer feeds."""
    def __init__(self):
        self.previous = None

    def observe(self, frame):
        import cv2
        thumbnail = cv2.cvtColor(cv2.resize(frame, (32,32)), cv2.COLOR_BGR2GRAY)
        cut = self.previous is not None and cv2.absdiff(thumbnail,self.previous).mean() > 70
        self.previous = thumbnail
        return bool(cut)
