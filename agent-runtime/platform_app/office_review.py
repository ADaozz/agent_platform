"""Host-only Office visual-review transport and durable evidence, shared by formats.

The historical ledger columns presentation_id/slide_id are retained for existing
PPTX databases; DOCX records use document identity/page number in those columns
and kind=docx-page. They are storage names, not an artifact-type constraint.
"""
import base64
import concurrent.futures
import hashlib
import io
import json
import sqlite3
import threading
import time
import uuid
from pathlib import Path
from pydantic import BaseModel, ValidationError

MAX_IMAGE_BYTES = 8 * 1024 * 1024
DEFAULT_TIMEOUT = 150.0

class VisionUnavailable(Exception):
    """No image-capable model, or the call could not produce a usable answer."""

    def __init__(self, code, message=''):
        super().__init__(message or code)
        self.code = code



def png_info(data):
    from PIL import Image
    if not data or len(data) > MAX_IMAGE_BYTES:
        raise VisionUnavailable('image_missing', 'rendered image is missing or oversized')
    with Image.open(io.BytesIO(data)) as image:
        if image.format != 'PNG':
            raise VisionUnavailable('image_missing', 'rendered image is not a PNG')
        rgb = image.convert('RGB')
        return dict(width=rgb.width, height=rgb.height, pixel_sha256=hashlib.sha256(rgb.tobytes()).hexdigest())



def parse(answer, schema):
    """Structured output (or its JSON text) -> validated dict. Raises VisionUnavailable."""
    if isinstance(answer, BaseModel):
        answer = answer.model_dump()
    elif isinstance(answer, str):
        try:
            answer = json.loads(answer)
        except ValueError as exc:
            raise VisionUnavailable('invalid_json', 'model reply is not JSON') from exc
    if not isinstance(answer, dict):
        raise VisionUnavailable('invalid_json', 'model returned no review')
    try:
        return schema.model_validate(answer).model_dump()
    except ValidationError as exc:
        error = exc.errors()[0]
        raise VisionUnavailable('schema_invalid', f'{"/".join(map(str, error["loc"]))}: {error["msg"]}'[:200]) from exc



def _decide(model_status, issues, checks, flags):
    blocking = [issue for issue in issues if issue['severity'] in ('critical', 'major') and not issue.get('dismissed')]
    confirmed = [issue for issue in blocking if issue['confidence'] in ('high', 'medium') and not issue.get('needs_verification')]
    if confirmed:
        if model_status == 'pass':
            flags.append(dict(type='status_contradiction', message='model said pass but reported confirmed blocking issues'))
        return 'failed'
    if blocking or model_status == 'uncertain' or any(item['verdict'] == 'uncertain' for item in checks.values()):
        return 'uncertain'
    if model_status == 'fail':
        flags.append(dict(type='unsupported_failure', message='model said fail without a confirmed critical or major issue'))
        return 'uncertain'
    return 'passed'



def review_with_retry(client, system, text, images, schema, evaluate):
    """One corrective retry when the answer does not fit the schema; returns (result, last answer)."""
    answer = client.complete(system, text, images, schema)
    try:
        return evaluate(answer), answer
    except VisionUnavailable as exc:
        if exc.code not in ('invalid_json', 'schema_invalid'):
            raise
        hint = f'\n\n上一次回答不符合要求（{exc}），请按要求的结构重新给出审查结果。'
        answer = client.complete(system, text + hint, images, schema)
        return evaluate(answer), answer



class ModelClient:
    """One multimodal request. ``invoke(system, text, images, schema)`` returns the structured review."""

    def __init__(self, model_id, invoke, timeout=DEFAULT_TIMEOUT):
        self.model_id = model_id
        self._invoke = invoke
        self.timeout = timeout

    def complete(self, system, text, images, schema):
        if not images:
            raise VisionUnavailable('image_missing', 'no image attached to the review request')
        executor = concurrent.futures.ThreadPoolExecutor(max_workers=1, thread_name_prefix='office-vision-call')
        future = executor.submit(self._invoke, system, text, images, schema)
        try:
            return future.result(timeout=self.timeout)
        except concurrent.futures.TimeoutError as exc:
            raise VisionUnavailable('timeout', f'vision model did not answer within {self.timeout:g}s') from exc
        except VisionUnavailable:
            raise
        except Exception as exc:  # provider errors may carry credentials; keep the type only
            raise VisionUnavailable('provider_error', type(exc).__name__) from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)



def langchain_invoker(chat_model):
    """Provider JSON mode with the review schema in the prompt; Pydantic validates the result.

    JSON mode rather than a forced function call: reasoning models (DeepSeek
    thinking mode) reject a forced tool_choice. Providers without JSON mode get
    the same prompt as a plain request.
    """
    import openai
    from langchain_core.exceptions import OutputParserException
    from langchain_core.messages import HumanMessage, SystemMessage
    from langchain_core.messages.content import create_image_block, create_text_block
    json_mode = [True]

    def invoke(system, text, images, schema):
        content = [create_text_block(text)]
        for mime, data in images:
            content.append(create_image_block(base64=base64.b64encode(data).decode('ascii'), mime_type=mime))
        instructions = system + '\n\n以 JSON 对象返回结果，结构遵循以下 JSON Schema：\n' + json.dumps(schema.model_json_schema(), ensure_ascii=False)
        messages = [SystemMessage(content=instructions), HumanMessage(content=content)]
        if json_mode[0]:
            try:
                return chat_model.with_structured_output(schema, method='json_mode').invoke(messages)
            except (OutputParserException, ValidationError) as exc:
                raise VisionUnavailable('schema_invalid', str(exc).splitlines()[0][:200]) from exc
            except openai.BadRequestError:
                json_mode[0] = False
        result = chat_model.invoke(messages)
        return result.content if isinstance(result.content, str) else ''.join(
            block.get('text', '') for block in result.content if isinstance(block, dict))
    return invoke



class ReviewLedger:
    """Host-private, append-only record of model reviews and issue dismissals."""

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



def failure(code, message=''):
    return dict(status='unavailable', error=dict(code=code, message=str(message)[:200]), issues=[], checks={}, flags=[], summary='')



class BackgroundReviews:
    """Bounded host queue; jobs never execute on the authoring thread."""
    def __init__(self, service, host=None, api=None):
        import logging
        self.service = service
        self.host = host or {}
        self.api = api
        self.log = logging.getLogger(__name__)
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=2, thread_name_prefix='office-review')
        self.inflight = set()
        self.lock = threading.Lock()
        self.closed = False
        self.timeout = float(self.host.get('vision_timeout', DEFAULT_TIMEOUT))

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
                self.log.error('Office review failed: %s', type(exc).__name__)
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

    def model(self):
        resolver = self.host.get('vision')
        if resolver is None:
            return None, 'vision review is not configured on this host'
        try:
            model_id, chat = resolver()
        except Exception as exc:
            return None, 'vision model could not be prepared: ' + type(exc).__name__
        if model_id is None:
            return None, chat
        api = self.api
        return api.ModelClient(model_id, api.langchain_invoker(chat) if hasattr(chat, 'invoke') else chat, self.timeout), None


def contact_sheet(images, columns=4, width=480):
    """Numbered thumbnail overview for deck review, built on the host."""
    from PIL import Image, ImageDraw, ImageFont
    thumbs = []
    for data in images:
        with Image.open(io.BytesIO(data)) as image:
            rgb = image.convert('RGB')
            height = round(rgb.height * width / rgb.width)
            thumbs.append(rgb.resize((width, height), Image.LANCZOS))
    if not thumbs:
        raise VisionUnavailable('image_missing', 'no rendered slides')
    gap, label = 16, 30
    cell_h = max(thumb.height for thumb in thumbs)
    rows = (len(thumbs) + columns - 1) // columns
    sheet = Image.new('RGB', (columns * width + (columns + 1) * gap, rows * (cell_h + label) + (rows + 1) * gap), '#DDE2E8')
    draw = ImageDraw.Draw(sheet)
    try:
        font = ImageFont.truetype('DejaVuSans-Bold.ttf', 20)
    except OSError:
        font = ImageFont.load_default()
    for index, thumb in enumerate(thumbs):
        row, column = divmod(index, columns)
        x = gap + column * (width + gap)
        y = gap + row * (cell_h + label + gap)
        draw.text((x, y), f'{index + 1:02d}', fill='#17324D', font=font)
        sheet.paste(thumb, (x, y + label))
    buffer = io.BytesIO()
    sheet.save(buffer, format='PNG', optimize=True)
    return buffer.getvalue()
