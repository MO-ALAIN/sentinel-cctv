"""ByteTrack adapter for elapsed media seconds; pinned to Ultralytics 8.4.142."""
from ultralytics.trackers.byte_tracker import BYTETracker


class PTSByteTracker(BYTETracker):
    def __init__(self, args, timeout_seconds=10):
        super().__init__(args)
        self.timeout_seconds = timeout_seconds
        self.max_frames_lost = 10**9  # Expiry below uses elapsed PTS, not frame count.
        self.last_pts = None
        self.last_seen_pts = {}

    def multi_predict(self, tracks):
        # Track.predict uses this tracker's own filter, avoiding class-global filters.
        for track in tracks:
            track.predict()

    def update_at(self, results, frame, pts):
        if self.last_pts is not None and pts <= self.last_pts:
            raise ValueError('Reset tracking before non-increasing media timestamps')
        dt = 0 if self.last_pts is None else pts-self.last_pts
        for axis in range(4):
            self.kalman_filter._motion_mat[axis,axis+4] = dt
        self.last_pts = pts
        for collection in (self.tracked_stracks,self.lost_stracks):
            expired = [t for t in collection if pts-self.last_seen_pts.get(t.track_id,pts) > self.timeout_seconds]
            for track in expired:
                track.mark_removed()
                self.last_seen_pts.pop(track.track_id,None)
            collection[:] = [t for t in collection if t not in expired]
        result = super().update(results,frame)
        for track in self.tracked_stracks:
            if track.frame_id == self.frame_id:
                self.last_seen_pts[track.track_id] = pts
        retained = {t.track_id for t in self.tracked_stracks+self.lost_stracks}
        self.last_seen_pts = {key:value for key,value in self.last_seen_pts.items() if key in retained}
        return result
