"""Explicit fields for timestamped detection evidence; never invent plate matches."""
FIELDS = ['observed_at_utc','timestamp_basis','media_offset_seconds','camera_id','camera_name','location','source_type','source_system','session_id','track_id','vehicle_type','classification_method','detector_class','detector_confidence','plate_number','plate_status','plate_score','bbox_pixels']

def detection_row(detection):
    plate = detection.get('anpr') or {}
    return {
        'observed_at_utc': detection.get('timestamp'),
        **{key: detection.get(key) for key in FIELDS if key in detection},
        'plate_number': plate.get('plate_number') if plate.get('status') == 'CONFIRMED' else '',
        'plate_status': plate.get('status') or 'NOT_CONFIRMED',
        'plate_score': plate.get('plate_confidence'),
        'bbox_pixels': ','.join(map(str,detection.get('bbox') or [])),
    }

def event_key(detection):
    return (detection.get('camera_id'),detection.get('session_id'),detection.get('track_id'),detection.get('timestamp'))
