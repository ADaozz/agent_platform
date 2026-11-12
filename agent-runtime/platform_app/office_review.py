"""Host-only Office visual-review evidence, shared by formats.

Visual review is performed by the main Agent through the skill CLIs; the host
never calls a model. It keeps a private, append-only record of submitted
reviews and issue dismissals, and runs bounded background verification jobs.

The historical ledger columns presentation_id/slide_id are retained for existing
PPTX databases; DOCX records use document identity/page number in those columns
and kind=docx-page. They are storage names, not an artifact-type constraint.
"""
import concurrent.futures
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path


class ReviewLedger:
    """Host-private, append-only record of visual reviews and issue dismissals."""

    def __init__(self, path):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        self.lock = threading.RLock()
        with self.connect() as c:
            c.execute('''CREATE TABLE IF NOT EXISTS reviews (id TEXT PRIMARY KEY, kind TEXT, presentation_id TEXT, path TEXT,
                slide_id TEXT, revision INTEGER, render_sha256 TEXT, pixel_sha256 TEXT, snapshot_sha256 TEXT, model_id TEXT,
                prompt_version TEXT, status TEXT, summary TEXT, issues TEXT, checks TEXT, flags TEXT, error TEXT,
                applied INTEGER, review_timestamp REAL, response_sha256 TEXT)''')
            c.execute('''CREATE TABLE IF NOT EXISTS decisions (id TEXT PRIMARY KEY, review_id TEXT, presentation_id TEXT,
                slide_id TEXT, revision INTEGER, decision TEXT, issue_ids TEXT, notes TEXT, actor TEXT, decided_at REAL)''')

    def connect(self):
        connection = sqlite3.connect(self.path, timeout=30)
        connection.row_factory = sqlite3.Row
        return connection

    def record(self, **values):
        values = dict(values)
        values.setdefault('id', uuid.uuid4().hex)
        values.setdefault('review_timestamp', time.time())
        for key in ('issues', 'checks', 'flags'):
            values[key] = json.dumps(values.get(key) or [], ensure_ascii=False)
        columns = ('id', 'kind', 'presentation_id', 'path', 'slide_id', 'revision', 'render_sha256', 'pixel_sha256', 'snapshot_sha256',
            'model_id', 'prompt_version', 'status', 'summary', 'issues', 'checks', 'flags', 'error', 'applied', 'review_timestamp', 'response_sha256')
        with self.lock, self.connect() as c:
            c.execute(f'INSERT INTO reviews ({",".join(columns)}) VALUES ({",".join("?" * len(columns))})', [values.get(key) for key in columns])
        return values['id']

    def mark_applied(self, review_id, applied):
        with self.lock, self.connect() as c:
            c.execute('UPDATE reviews SET applied=? WHERE id=?', (1 if applied else 0, review_id))

    def get(self, review_id):
        with self.connect() as c:
            row = c.execute('SELECT * FROM reviews WHERE id=?', (review_id,)).fetchone()
        if row is None:
            return None
        value = dict(row)
        for key in ('issues', 'checks', 'flags'):
            value[key] = json.loads(value[key] or '[]')
        return value

    def decide(self, **values):
        values = dict(values)
        if values.get('decision')!='dismiss_issues':
            raise ValueError('Manual visual acceptance/rejection is no longer supported')
        values.setdefault('id', uuid.uuid4().hex)
        values.setdefault('decided_at', time.time())
        values['issue_ids'] = json.dumps(values.get('issue_ids') or [])
        columns = ('id', 'review_id', 'presentation_id', 'slide_id', 'revision', 'decision', 'issue_ids', 'notes', 'actor', 'decided_at')
        with self.lock, self.connect() as c:
            c.execute(f'INSERT INTO decisions ({",".join(columns)}) VALUES ({",".join("?" * len(columns))})', [values.get(key) for key in columns])
        return values['id']

    def decision(self, decision_id):
        with self.connect() as c:
            row = c.execute('SELECT * FROM decisions WHERE id=?', (decision_id,)).fetchone()
        return dict(row) if row else None


class BackgroundReviews:
    """Bounded host queue; jobs never execute on the authoring thread."""
    def __init__(self, service, host=None):
        import logging
        self.service = service
        self.host = host or {}
        self.log = logging.getLogger(__name__)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='office-review')
        self.inflight = set()
        self.lock = threading.Lock()
        self.closed = False

    def close(self):
        self.closed = True
        self.executor.shutdown(wait=False, cancel_futures=True)

    def schedule(self, key, function, *args):
        with self.lock:
            if self.closed or key in self.inflight:
                return False
            self.inflight.add(key)
        def run():
            try:
                function(*args)
            except Exception as exc:
                self.log.error('Office review job failed: %s', type(exc).__name__)
            finally:
                with self.lock:
                    self.inflight.discard(key)
                if not self.closed:
                    try:
                        self.service.sync()
                    except Exception as exc:
                        self.log.error('Office review sync failed: %s', type(exc).__name__)
        try:
            self.executor.submit(run)
        except RuntimeError:
            with self.lock:
                self.inflight.discard(key)
            return False
        return True
