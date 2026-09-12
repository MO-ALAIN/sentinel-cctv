"""Score confirmed plate observations against independently labelled media intervals."""
import argparse
import hashlib
import json
import math
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


def normalize(value):
    return re.sub(r'[^A-Z0-9]','',value.upper())


def score(events, observations):
    """Maximum one-to-one exact-plate matching; duplicate observations count as false positives."""
    edges=[]
    for event in events:
        edges.append([i for i,row in enumerate(observations)
                      if normalize(row['plate_number'])==normalize(event['plate_number'])
                      and event['start_seconds']<=row['media_offset_seconds']<=event['end_seconds']])
    owners={}
    def match(event, visited):
        for row in edges[event]:
            if row in visited: continue
            visited.add(row)
            if row not in owners or match(owners[row],visited):
                owners[row]=event
                return True
        return False
    for event in range(len(events)): match(event,set())
    matched_events=set(owners.values())
    return {'matches':[{'event_index':event,'sighting_id':observations[row]['id']} for row,event in sorted(owners.items())],
            'missed_event_indices':[i for i in range(len(events)) if i not in matched_events],
            'false_positive_sighting_ids':[row['id'] for i,row in enumerate(observations) if i not in owners]}


def evaluate(manifest, connection):
    if not manifest.get('windows'): raise ValueError('At least one fully labelled window is required')
    reports=[]; previous=[]; totals={'true_positives':0,'false_positives':0,'false_negatives':0}
    for window in manifest['windows']:
        camera,session=window['camera_id'],window['session_id']
        start,end=window['start_seconds'],window['end_seconds']
        if not camera or not session or not all(math.isfinite(x) for x in (start,end)) or not 0<=start<end:
            raise ValueError('Each window needs a camera, session and valid media interval')
        if any(c==camera and s==session and max(start,a)<=min(end,b) for c,s,a,b in previous):
            raise ValueError('Evaluation windows must not overlap within a camera session')
        previous.append((camera,session,start,end))
        events=window.get('events',[])
        for event in events:
            if not normalize(event['plate_number']) or not start<=event['start_seconds']<=event['end_seconds']<=end:
                raise ValueError('Every labelled appearance must lie inside its evaluation window')
        rows=[dict(row) for row in connection.execute(
            "SELECT id,plate_number,media_offset_seconds,timestamp_basis FROM plate_sightings "
            "WHERE camera_id=? AND session_id=? AND status='CONFIRMED' "
            "AND media_offset_seconds BETWEEN ? AND ? ORDER BY media_offset_seconds,id",(camera,session,start,end))]
        result=score(events,rows)
        totals['true_positives']+=len(result['matches'])
        totals['false_positives']+=len(result['false_positive_sighting_ids'])
        totals['false_negatives']+=len(result['missed_event_indices'])
        reports.append(dict(camera_id=camera,session_id=session,start_seconds=start,end_seconds=end,
                            labelled_events=events,confirmed_observations=rows,**result))
    tp,fp,fn=(totals[key] for key in ('true_positives','false_positives','false_negatives'))
    totals.update(precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,
                  f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else None)
    return {'metrics':totals,'windows':reports,
            'method':'One exact normalized plate per labelled camera appearance, inside a fully labelled media window. Duplicate and incorrect confirmed observations count as false positives.',
            'limits':'Event precision/recall only. This does not measure character accuracy, calibrated confidence, live alert latency, or unlabelled footage. Include all eligible appearances, including misses; do not label only successful reads.'}


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',required=True,type=Path)
    parser.add_argument('--labels',required=True,type=Path)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    if not args.database.is_file(): parser.error('Database does not exist')
    raw=args.labels.read_bytes()
    connection=sqlite3.connect(args.database.resolve().as_uri()+'?mode=ro',uri=True)
    connection.row_factory=sqlite3.Row
    try: report=evaluate(json.loads(raw),connection)
    finally: connection.close()
    report.update(generated_at=datetime.now(timezone.utc).isoformat(),labels_sha256=hashlib.sha256(raw).hexdigest())
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['metrics'],indent=2))


if __name__=='__main__': main()
