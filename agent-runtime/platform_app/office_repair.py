"""Shared deterministic repair progress policy; never consumes visual findings.

There is no round limit. Revisions and ZIP timestamps are not evidence of progress.
Adapters supply stable issue keys, deterministic evidence and optional geometric
magnitudes. History is JSON data so restarts retain cycle detection.
"""
import hashlib
import io
import json
import math
import zipfile


def digest(value):
    return hashlib.sha256(json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':')).encode()).hexdigest()


def package_fingerprint(data):
    result=hashlib.sha256()
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        for name in sorted(archive.namelist()):
            value=archive.read(name);result.update(name.encode()+b'\0'+str(len(value)).encode()+b'\0'+value)
    return result.hexdigest()


def issue(key,evidence=None,magnitude=None):
    item=dict(key=digest(key),evidence=evidence)
    if magnitude is not None and math.isfinite(float(magnitude)):
        item['magnitude']=round(max(0,float(magnitude)),8)
    return item


def observe(history,issues,content,revision):
    """Return a new durable history and control verdict for an actual recheck.

    Repeating a diagnostic read of the same revision is idempotent. After edits,
    resolved targets or strictly improving measured geometry allow continuation;
    repeated evidence, unchanged content and recurring states stop autonomy.
    """
    records=list((history or {}).get('observations',[]))
    issues=sorted(issues,key=lambda item:(item['key'],digest(item)))
    snapshot=dict(revision=revision,content=content,issues=issues,fingerprint=digest(issues))
    reason=None
    if not issues:
        return dict(observations=[]),dict(status='passed',stop_reason=None,autonomous_repair_allowed=False)
    if records:
        prior=records[-1]
        if snapshot==prior:
            return history,dict((history or {})['control'])
        if any(r['fingerprint']==snapshot['fingerprint'] for r in records[:-1]) or any(r['content']==content for r in records[:-1]):
            reason='repair_cycle'
        elif prior['fingerprint']==snapshot['fingerprint']:
            reason='repeated_errors'
        elif prior['content']==content:
            reason='no_progress'
        else:
            def measures(items):
                grouped={}
                for item in items:grouped.setdefault(item['key'],[]).append(item.get('magnitude'))
                return {key:sum(values) if all(v is not None for v in values) else None for key,values in grouped.items()}
            before=measures(prior['issues']);after=measures(issues)
            resolved=(before.keys()-after.keys()) or len(issues)<len(prior['issues'])
            comparable=before.keys()==after.keys() and all(before[k] is not None and after[k] is not None for k in before)
            improved=comparable and all(after[k]<=before[k]+1e-8 for k in before) and any(after[k]<before[k]-1e-8 for k in before)
            if not resolved and not improved:reason='no_progress'
    control=dict(status='stopped' if reason else 'progressing',stop_reason=reason,autonomous_repair_allowed=reason is None)
    records.append(snapshot)
    return dict(observations=records,control=control),control
