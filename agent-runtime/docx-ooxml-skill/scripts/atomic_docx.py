"""Transactional, bounded DOCX edits. SQLite snapshots are the recovery authority.

The visible DOCX is published atomically after a durable commit. pending_publish
repairs a process crash between the database commit and os.replace. flock covers
CLI and HTTP processes; revisions never decrease, including restore.
"""
import fcntl
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import re
import tempfile
import time
import zipfile

_spec = importlib.util.spec_from_file_location('ooxml_engine', Path(__file__).with_name('office_docx.py'))
o = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(o)
_shared_path = Path(__file__).resolve().parents[2] / 'platform_app' / 'artifact_runtime.py'
if not _shared_path.is_file():
    _shared_path = Path(__file__).with_name('artifact_runtime.py')
_shared_spec = importlib.util.spec_from_file_location('artifact_runtime', _shared_path)
_shared = importlib.util.module_from_spec(_shared_spec)
_shared_spec.loader.exec_module(_shared)
ID = re.compile(r'^[\w.-]{1,80}$')
BLOCK_NS = 'urn:deep-agent:docx:blocks:v1'
BLOCK_ID = '{%s}id' % BLOCK_NS
MAX_DIRTY = 3


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value) or value in ('.', '..'):
        raise ValueError('Invalid stable identifier')
    return value


def packed(parts):
    result = o.validate_parts(parts)
    if not result['ok']:
        raise ValueError('OOXML validation failed: ' + str(result['errors']))
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w', zipfile.ZIP_DEFLATED) as z:
        for name, data in parts.items():
            z.writestr(name, data)
    return stream.getvalue()


def publish(path, data):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.' + path.name, delete=False) as f:
            temporary = Path(f.name)
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(temporary, path)
        fd = os.open(path.parent, os.O_DIRECTORY)
        try:
            os.fsync(fd)
        finally:
            os.close(fd)
    finally:
        if temporary:
            temporary.unlink(missing_ok=True)


def mark_blocks(parts):
    root = o.parse_xml(parts[o.MAIN])
    mc = 'http://schemas.openxmlformats.org/markup-compatibility/2006'
    if 'dab' not in root.nsmap:
        replacement = o.etree.Element(root.tag, nsmap={**root.nsmap, 'dab': BLOCK_NS, 'mc': mc})
        replacement.attrib.update(root.attrib)
        replacement.text = root.text
        replacement.extend(list(root))
        root = replacement
    ignorable = root.get('{%s}Ignorable' % mc, '').split()
    if 'dab' not in ignorable:
        root.set('{%s}Ignorable' % mc, ' '.join([*ignorable, 'dab']))
    ids = [b.get(BLOCK_ID) for b in root.iter() if b.get(BLOCK_ID)]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate stable block IDs')
    used = set(ids)
    # Existing template paragraphs, table cells, tables and image paragraphs get
    # deterministic IDs once; future edits preserve these attributes. No index API.
    for i, block in enumerate(root.iter()):
        if block.tag in (o.q(o.W, 'p'), o.q(o.W, 'tbl')) and not block.get(BLOCK_ID):
            name = 'template-%04d' % i
            while name in used:
                name += '-x'
            block.set(BLOCK_ID, name)
            used.add(name)
    parts[o.MAIN] = o.xml_bytes(root)
    return parts


class DocumentStore(_shared.ArtifactStore):
    def __init__(self, path, temporary_root=None):
        super().__init__(path, '.docx', '.docx-state', temporary_root)

    def _publish(self, path, data):
        publish(path, data)

    def commit(self, c, state, data, operation_id, request, changed, kind='document_revision', extra=None):
        revision = state['revision'] + 1
        digest = hashlib.sha256(data).hexdigest()
        result = dict(status='committed', document_id=state['document_id'], revision=revision,
            sha256=digest, operation_id=operation_id, changed_blocks=changed, needs_preview=True,
            path=self.path.name, preview_ready=False, committed_at=time.time())
        if extra:
            result.update(extra)
        dirty = state.get('dirty', 0) + 1
        gate = state.get('gate', 'open')
        if gate == 'open' and dirty >= MAX_DIRTY:
            gate = 'checkpoint'
        if 'external' in request:
            result.update(external_unreviewed=True, gate='checkpoint')
        state['aesthetic_reviews'] = {}
        state['document_check'] = None
        state['document_review'] = None
        state['visual_request'] = None
        state['delivery_status'] = 'draft_pending_check'
        state['delivery_requested'] = False
        state.update(revision=revision, sha256=digest, pending_publish=True, finalized=False,
            dirty=dirty, pages=[], preview_ready=False, gate=gate)
        self.persist_revision(c, state, data, result, request, operation_id, kind)
        return result

    def init(self, document_id, template=None, mode='normal', design=None, columns=None, quality_contract=None):
        identifier(document_id)
        if quality_contract is not None and (type(quality_contract) is not int or quality_contract not in (1,2)):raise ValueError('Unknown quality contract')
        if mode not in ('normal', 'strict'):
            raise ValueError('Unknown review mode')
        with self.locked() as (c, state):
            if state:
                if state['document_id'] != document_id:
                    raise ValueError('Document identity mismatch')
                return state
            if self.path.exists():
                raise ValueError('Document exists; use track_external or a different output path')
            parts = o.read_parts(template) if template else o.default_package()
            selected_design = None
            if design and not template:
                helper = _sibling('document_design')
                selected_design = helper.inspect_style(design)
                if columns is not None:selected_design['page']['columns']=columns
                parts = helper.apply(parts, selected_design, o)
            parts = mark_blocks(parts)
            manifest = _template_manifest(parts, template) if template else None
            data = packed(parts)
            state = dict(document_id=document_id, revision=-1, mode=mode, dirty=-1, pages=[], gate='open',
                template_manifest=manifest, selected_design=selected_design, quality_contract=quality_contract or (2 if selected_design and selected_design.get('version',1)>=2 else 1))
            self.commit(c, state, data, '__init__', {'template': str(template)}, [], 'document_initialized')
            return state

    def assert_current(self, state, base_revision=None):
        if state is None:
            raise ValueError('Document not initialized')
        if base_revision is not None and (type(base_revision) is not int or state['revision'] != base_revision):
            raise ValueError('Revision conflict; inspect status and rebase')
        if not self.path.exists() or o.sha(self.path) != state['sha256']:
            raise ValueError('External modification detected; track before editing')

    def metadata(self, external=False):
        """Current state without unpacking a DOCX or loading its revision history."""
        with self.locked() as (c, state):
            if state is None:
                raise ValueError('Document not initialized')
            result = dict(state)
            if external:
                try:
                    result['external_conflict'] = o.sha(self.path) != state['sha256']
                except OSError:
                    result['external_conflict'] = True
            return result

    def status(self, committed=False):
        with self.locked() as (c, state):
            if committed:
                if state is None:
                    raise ValueError('Document not initialized')
                row = c.execute('SELECT docx FROM revisions WHERE revision=?', (state['revision'],)).fetchone()
                parts = o.read_parts(io.BytesIO(row[0]))
            else:
                self.assert_current(state)
                parts = o.read_parts(self.path)
            root = o.parse_xml(parts[o.MAIN])
            result = dict(state)
            if committed:
                try:
                    result['external_conflict'] = o.sha(self.path) != state['sha256']
                except OSError:
                    result['external_conflict'] = True
            result['blocks'] = [dict(block_id=b.get(BLOCK_ID), type=o.etree.QName(b).localname, text=o.ptext(b)[:500])
                for b in root.iter() if b.get(BLOCK_ID)]
            result['styles'] = [node.get(o.q(o.W, 'styleId')) for node in o.parse_xml(parts.get('word/styles.xml', ('<w:styles xmlns:w="'+o.W+'"/>').encode())).iter(o.q(o.W, 'style'))]
            result['history'] = [json.loads(r[0]) for r in c.execute('SELECT result FROM revisions ORDER BY revision')]
            return result

    def apply_one(self, request, asset_root=None):
        identifier(request['operation_id'])
        with self.locked() as (c, state):
            if state is None or request['document_id'] != state['document_id']:
                raise ValueError('Document identity mismatch')
            previous = c.execute('SELECT request,result FROM revisions WHERE operation_id=?', (request['operation_id'],)).fetchone()
            if previous:
                if json.loads(previous[0]) != request:
                    raise ValueError('Operation ID reused with different payload')
                return json.loads(previous[1])
            self.assert_current(state, request['base_revision'])
            op = request['operation']
            kind = op.get('type')
            repairs = {'replace_text', 'set_paragraph_style', 'set_paragraph_format', 'delete_block', 'set_table_format', 'set_page',
                'slot.fill', 'document.recolor', 'part.replace_text', 'update_toc',
                'set_table_cell', 'format_text', 'set_header_footer'}
            if state['gate'] != 'open' and kind not in repairs:
                raise ValueError('Page checkpoint required before adding content: ' + state['gate'])
            if state['dirty'] >= MAX_DIRTY * 2:
                raise ValueError('Checkpoint required before further changes')
            parts = o.read_parts(self.path)
            try:
                parts, changed, extra = mutate(parts, op, Path(asset_root or self.path.parent))
            except (o.etree.XMLSyntaxError, KeyError, TypeError) as exc:
                raise ValueError('Invalid atomic operation: ' + str(exc)) from exc
            return self.commit(c, state, packed(parts), request['operation_id'], request, changed, extra=extra)

    def _workflow(self, name, *args, **kwargs):
        from types import SimpleNamespace
        api = SimpleNamespace(o=o, identifier=identifier, BLOCK_ID=BLOCK_ID,
            BLOCK_NS=BLOCK_NS, packed=packed, mutate=mutate, _sibling=_sibling, repair_policy=repair_policy())
        return getattr(_sibling('document_workflow'), name)(self, *args, a=api, **kwargs)

    def save_plan(self, request):
        return self._workflow('save_plan', request)

    def apply_section(self, request, asset_root=None):
        result = self._workflow('apply_section', request, asset_root)
        # The durable transaction is already committed. Render failure is reported
        # as a failed check, never disguised as a rolled-back transaction.
        current = self.status(committed=True)
        if current['revision'] == result['revision'] and current.get('render_revision') != result['revision']:
            try:
                self.check_document(section_id=request['section_id'])
            except ValueError:
                # A newer commit supersedes this check; the accepted transaction
                # still has a stable idempotent result. Other check errors surface.
                if self.status(committed=True)['revision'] == result['revision']:
                    raise
        return result

    def check_document(self, final=False, section_id=None, auto_repair=True):
        result=self._workflow('check_document', final, section_id=section_id)
        state=self.metadata()
        if final and auto_repair and state.get('quality_contract',1)>=2 and not result['passed']:
            if state.get('auto_repair_stopped_revision')==result['revision']:
                summary=state.get('repair_summary') or {}
                return dict(result,repair_summary=dict(repair_attempts=summary.get('attempts',0),remaining=result['repair_targets'],stop_reason=summary.get('stop_reason'),exhausted=True))
            report=self.repair_document(result['revision'],'auto-repair-r'+str(result['revision']))
            if report['exhausted']:
                with self.locked() as(c,current):
                    self.assert_current(current,report['revision'])
                    current['auto_repair_stopped_revision']=report['revision']
                    self.save_state(c,current);c.commit()
            return dict(report['recheck'],repair_summary={k:report[k] for k in ('repair_attempts','remaining','exhausted','stop_reason')})
        return result

    def repair_document(self, base_revision, operation_id, max_attempts=None):
        # Deprecated argument retained for existing callers; progress governs stopping.
        if max_attempts is not None and (type(max_attempts) is not int or max_attempts<1):raise ValueError('Invalid legacy max_attempts')
        return self._workflow('repair_document', base_revision, operation_id)

    def prepare_restore(self, c, state, revision):
        # Replay metadata transitions, including restores followed by more edits.
        # Looking up only the most recent plan edit would resurrect a superseded
        # plan after restoring a revision that was itself built from a restore.
        metadata = {}
        plan, workflow = None, False
        for row in c.execute('SELECT revision,request,result FROM revisions WHERE revision<=? ORDER BY revision', (revision,)):
            request, result = json.loads(row['request']), json.loads(row['result'])
            if 'restore' in request:
                plan, workflow = metadata[request['restore']]
            else:
                if 'plan' in result:
                    plan = result['plan']
                if 'section_id' in request:
                    workflow = True
            metadata[row['revision']] = (plan, workflow)
        state.update(document_plan=plan, sections={}, document_check=None)
        if workflow:
            state['workflow_version'] = 1
        else:
            state.pop('workflow_version', None)
        return state

    def track_external(self, document_id=None):
        """Observe native write/execute changes without calling them reviewed/atomic."""
        with self.locked() as (c, state):
            if not self.path.is_file() or self.path.is_symlink():
                return None
            digest = o.sha(self.path)
            if state and digest == state['sha256']:
                return None
            # Invalid writes never replace the last committed snapshot.
            parts = o.read_parts(self.path)
            data = self.path.read_bytes()
            if not o.validate_parts(parts)['ok']:
                raise ValueError('External DOCX is invalid')
            if state is None:
                state = dict(document_id=identifier(document_id or self.path.stem), revision=-1, mode='normal', dirty=0)
            result = self.commit(c, state, data, 'external-' + str(state['revision'] + 1), {'external': digest}, ['*'])
            state.update(gate='checkpoint', external_unreviewed=True)
            self.save_state(c, state)
            c.commit()
            return result

    def render_snapshot(self, revision):
        """One renderer per immutable revision, shared by live preview and QA."""
        data = self.snapshot(revision)
        digest = hashlib.sha256(data).hexdigest()
        output = self.render_directory(revision)
        output.mkdir(parents=True, exist_ok=True)
        with (output / 'render.lock').open('a') as lock:
            fcntl.flock(lock, fcntl.LOCK_EX)
            manifest_file = output / 'render.json'
            if manifest_file.exists():
                manifest = json.loads(manifest_file.read_text())
                if manifest.get('sha256') == digest and (output / 'preview.pdf').is_file() and all((output / image).is_file() for image in manifest.get('images', [])):
                    if 'page_hashes' not in manifest:
                        self._share_pages(output, manifest)
                        publish(manifest_file, json.dumps(manifest).encode())
                    return output, manifest
            source = output / self.path.name
            publish(source, data)
            render_started = time.monotonic()
            manifest = o.run_render(source, output)
            if manifest is None:  # deterministic renderer used by storage tests
                import pymupdf as fitz
                with fitz.open(output / 'preview.pdf') as pdf:
                    manifest = dict(sha256=digest, page_count=len(pdf), images=[f'page-{i+1:03d}.png' for i in range(len(pdf))])
            manifest['render_ms'] = round((time.monotonic() - render_started) * 1000, 2)
            manifest['sha256'] = digest
            self._share_pages(output, manifest)
            publish(manifest_file, json.dumps(manifest).encode())
            return output, manifest

    def page_directory(self):
        return self.render_root / 'pages'

    def _share_pages(self, output, manifest):
        """Layout is global, so every revision is paginated in full; identical pages keep one
        content-addressed image so viewers reload only the pages whose pixels changed."""
        shared = self.page_directory()
        shared.mkdir(parents=True, exist_ok=True)
        hashes = []
        for image in manifest['images']:
            data = (output / image).read_bytes()
            name = hashlib.sha256(data).hexdigest()[:24]
            target = shared / (name + '.png')
            if not target.is_file():
                publish(target, data)
            hashes.append(name)
        manifest['page_hashes'] = hashes

    def preview_failed(self, error):
        with self.locked() as (c, state):
            if state is None:
                return
            state['preview_error'] = error
            self.save_state(c, state)
            event = dict(type='document_preview_error', document_id=state['document_id'], revision=state['revision'],
                path=self.path.name, preview_error=error)
            c.execute('INSERT INTO events(data) VALUES (?)', (json.dumps(event),))
            c.commit()
            return event

    def preview(self, revision):
        output, manifest = self.render_snapshot(revision)
        with self.locked() as (c, state):
            if state is None or revision != state['revision'] or revision <= state.get('preview_revision', -1):
                return None
            state.update(preview_revision=revision, preview_pages=manifest['page_count'], preview_page_hashes=manifest['page_hashes'],
                preview_error=None, preview_ready=True)
            self.save_state(c, state)
            event = dict(type='document_preview', document_id=state['document_id'], revision=state['revision'],
                preview_revision=revision, preview_pages=manifest['page_count'], preview_page_hashes=manifest['page_hashes'],
                path=self.path.name, preview_ready=True)
            c.execute('INSERT INTO events(data) VALUES (?)', (json.dumps(event),))
            c.commit()
            return event

    def checkpoint(self, final=False):
        from importlib.util import spec_from_file_location, module_from_spec
        spec = spec_from_file_location('page_review', Path(__file__).with_name('page_review.py'))
        review = module_from_spec(spec)
        spec.loader.exec_module(review)
        # Render an immutable snapshot outside the commit lock; stale results are rejected.
        current = self.status()
        revision = current['revision']
        hashes = []
        try:
            output, manifest = self.render_snapshot(revision)
            hashes = manifest['page_hashes']
            source = output / self.path.name
            pages = review.review_pages(source, output, o, final=final, render=False)
            failure = None
        except (OSError, ValueError, RuntimeError, ImportError, TimeoutError) as exc:
            pages, failure = [], type(exc).__name__ + ': ' + str(exc)[:300]
        with self.locked() as (c, state):
            self.assert_current(state, revision)
            old = {p['fingerprint']: p for p in state.get('last_pages', []) if p.get('checks', {}).get('visual_review') in ('passed', 'failed')}
            for page in pages:
                if page['fingerprint'] in old and page['checks']['automatic_passed']:
                    page['checks']['visual_review'] = old[page['fingerprint']]['checks']['visual_review']
                    page['evidence'] = old[page['fingerprint']].get('evidence')
                    if page['checks']['visual_review'] == 'failed':
                        page['status'] = 'failed'
                    elif page['complete']:
                        page['status'] = 'passed'
            previous_check=state.get('document_check') or {}
            changed=bool(previous_check and (failure or [p['fingerprint'] for p in previous_check.get('pages',[])]!=[p['fingerprint'] for p in pages]))
            if changed:
                state.update(document_check=None,visual_request=None,document_review=None,aesthetic_reviews={},delivery=None,delivery_status='draft_pending_check',finalized=False)
            state.update(pages=pages, last_pages=pages, render_revision=revision, render_error=failure, dirty=0)
            if not failure:
                state.update(preview_revision=revision, preview_pages=len(pages), preview_page_hashes=hashes, preview_error=None, preview_ready=True)
            complete = [p for p in pages if p['complete']]
            if failure or any(not p['checks']['automatic_passed'] or p['checks']['visual_review'] == 'failed' for p in pages):
                state['gate'] = 'failed'
            elif state['mode'] == 'strict' and any(p['status'] != 'passed' for p in complete):
                state['gate'] = 'visual_pending'
            else:
                state['gate'] = 'open'
            self.save_state(c, state)
            event = dict(type='document_review', document_id=state['document_id'], revision=revision,
                pages=pages, gate=state['gate'], render_error=failure, path=self.path.name,
                **(dict(document_check=None,visual_request=None,document_review=None,aesthetic_reviews={},delivery=None,delivery_status='draft_pending_check',finalized=False) if changed else {}),
                **({} if failure else dict(preview_revision=revision, preview_pages=len(pages), preview_page_hashes=hashes,
                    preview_ready=True, render_directory=str(output))))
            c.execute('INSERT INTO events(data) VALUES (?)', (json.dumps(event),))
            c.commit()
            return event

    def visual_review(self, revision, page, passed, reviewer, notes):
        if type(passed) is not bool:
            raise ValueError('Visual verdict must be a boolean')
        if reviewer not in ('human', 'vision_model') or not isinstance(notes, str) or not notes.strip():
            raise ValueError('Actual visual review requires reviewer and evidence notes')
        with self.locked() as (c, state):
            self.assert_current(state, revision)
            if state.get('render_revision') != revision:
                raise ValueError('Render checkpoint is stale')
            target = next((p for p in state['pages'] if p['page'] == page), None)
            if target is None or not target['checks']['automatic_passed']:
                raise ValueError('Page must pass automatic checks first')
            target['checks']['visual_review'] = 'passed' if passed else 'failed'
            target['evidence'] = dict(reviewer=reviewer, notes=notes, reviewed_at=time.time())
            target['status'] = ('passed' if target['complete'] else 'writing') if passed else 'failed'
            state['last_pages'] = state['pages']
            if not passed:
                state['gate'] = 'failed'
            elif all(p['checks']['automatic_passed'] and (not p['complete'] or p['status'] == 'passed') for p in state['pages']):
                state['gate'] = 'open'
            self.save_state(c, state)
            event = dict(type='document_review', document_id=state['document_id'], revision=revision, path=self.path.name,
                pages=state['pages'], gate=state['gate'])
            c.execute('INSERT INTO events(data) VALUES (?)', (json.dumps(event),))
            c.commit()
            return event

    def finalize(self, base_revision):
        with self.locked() as (c, state):
            self.assert_current(state, base_revision)
            workflow = state.get('workflow_version') == 1 or state.get('quality_contract',1)>=2
            check = state.get('document_check') or {}
            if state.get('render_revision') != base_revision or not state['pages'] or state['gate'] != 'open' or (not workflow and any(p['status'] != 'passed' for p in state['pages'])) or (workflow and (check.get('revision') != base_revision or not check.get('passed') or not check.get('final'))):
                raise ValueError('Final checkpoint and actual visual review of every page required')
            render_dir = self.render_directory(base_revision)
            if not (render_dir / 'render.json').is_file() or any(not (render_dir / p['image']).is_file() for p in state['pages']):
                raise ValueError('Reviewed render artifacts are missing; render and review again')
            if state.get('quality_contract',1)>=2:
                if not check.get('collision_check_executed'):raise ValueError('Final collision and layout audit required')
                summary=_sibling('quality_status').delivery(state)
                state['delivery_status']=summary['status']
                state['finalized']=summary['status']=='accepted'
                state['delivery']=summary
                state['delivery_requested']=True
                self.save_state(c,state)
                c.execute('INSERT INTO events(data) VALUES (?)',(json.dumps(dict(type='document_finalized',document_id=state['document_id'],revision=base_revision,path=self.path.name,finalized=state['finalized'],delivery_status=state['delivery_status'],delivery=summary)),));c.commit()
                return dict(summary,publication_status='finalized' if state['finalized'] else 'draft',document_id=state['document_id'],editable=True)
            state['finalized'] = True
            state['external_unreviewed'] = False
            self.save_state(c, state)
            c.execute('INSERT INTO events(data) VALUES (?)', (json.dumps(dict(type='document_finalized', document_id=state['document_id'], revision=base_revision, path=self.path.name, finalized=True)),))
            c.commit()
            return dict(status='finalized', document_id=state['document_id'], revision=base_revision, sha256=state['sha256'],
                structure=(state.get('document_check') or {}).get('structure_passed'),
                layout=(state.get('document_check') or {}).get('layout_passed'),
                visual_review=state.get('aesthetic_reviews', {}),
                visual_status='pending' if len(state.get('aesthetic_reviews', {})) < len(state['pages']) else
                    'unavailable' if any(r.get('status') == 'unavailable' for r in state['aesthetic_reviews'].values()) else
                    'completed', editable=True)


def mutate(parts, op, asset_root):
    if not isinstance(op, dict) or len(json.dumps(op, ensure_ascii=False)) > 24000:
        raise ValueError('Operation exceeds bounded payload')
    parts = mark_blocks(parts)
    kind = op.get('type')
    if kind in ('block.clone', 'section.clone', 'slot.fill', 'part.replace_text'):
        updated, changed, extra = _template_blocks().apply(parts, op, o, BLOCK_ID)
        return mark_blocks(updated), changed, extra
    if kind == 'document.recolor':
        return _template_styles().recolor(parts, op, o)
    root = o.parse_xml(parts[o.MAIN])
    body = root.find(o.q(o.W, 'body'))
    block_id = identifier(op.get('block_id', 'page-layout'))
    matches = root.xpath('//*[@b:id=$id]', namespaces={'b': BLOCK_NS}, id=block_id)
    target = matches[0] if len(matches) == 1 else None
    adding = kind in ('append_paragraph', 'append_table', 'insert_image', 'insert_block',
                      'insert_equation', 'insert_chart', 'insert_caption', 'insert_toc',
                      'insert_table', 'insert_image_row')
    academic = _sibling('academic_blocks')
    rich = _sibling('rich_blocks')
    if adding:
        if matches:
            raise ValueError('Duplicate block_id')
        if kind == 'append_paragraph':
            text = op.get('text')
            if text is not None and (not isinstance(text, str) or len(text) > 3000 or '\n' in text or '\r' in text):
                raise ValueError('One paragraph, maximum 3000 characters')
            style = op.get('style', 'Normal')
            o.require_style(parts, style)
            node = o.etree.Element(o.q(o.W, 'p'))
            prop = o.etree.SubElement(node, o.q(o.W, 'pPr'))
            o.etree.SubElement(prop, o.q(o.W, 'pStyle')).set(o.q(o.W, 'val'), style)
            node.extend(rich.inline_nodes(o, text=text, runs=op.get('runs')))
            if op.get('ref_id'):
                rich.bookmark_paragraph(o, root, node, identifier(op['ref_id']))
        elif kind == 'append_table':
            rows = op['rows']
            if not isinstance(rows, list) or not 1 <= len(rows) <= 60 or any(not isinstance(r, list) or not 1 <= len(r) <= 8 for r in rows) or len({len(r) for r in rows}) != 1:
                raise ValueError('A bounded table requires 1-60 rows and 1-8 uniform columns')
            if any(not isinstance(t, str) or len(t) > 300 for row in rows for t in row):
                raise ValueError('Table cells must be strings of at most 300 characters')
            widths = op.get('column_widths_twips', [9000 // len(rows[0])] * len(rows[0]))
            if not isinstance(widths, list) or len(widths) != len(rows[0]) or any(type(w) is not int or not 300 <= w <= 15000 for w in widths) or sum(widths) > 15000:
                raise ValueError('Invalid bounded table column widths')
            node = o.etree.Element(o.q(o.W, 'tbl'))
            prop = o.etree.SubElement(node, o.q(o.W, 'tblPr'))
            o.etree.SubElement(prop, o.q(o.W, 'tblW'), attrib={o.q(o.W, 'w'): str(sum(widths)), o.q(o.W, 'type'): 'dxa'})
            borders = o.etree.SubElement(prop, o.q(o.W, 'tblBorders'))
            for edge in ('top', 'left', 'bottom', 'right', 'insideH', 'insideV'):
                o.etree.SubElement(borders, o.q(o.W, edge), attrib={o.q(o.W, 'val'): 'single', o.q(o.W, 'sz'): '4', o.q(o.W, 'color'): 'BCC4CC'})
            o.etree.SubElement(prop, o.q(o.W, 'tblLayout'), attrib={o.q(o.W, 'type'): 'fixed'})
            grid = o.etree.SubElement(node, o.q(o.W, 'tblGrid'))
            for width in widths:
                o.etree.SubElement(grid, o.q(o.W, 'gridCol'), attrib={o.q(o.W, 'w'): str(width)})
            for row_index, row in enumerate(rows):
                tr = o.etree.SubElement(node, o.q(o.W, 'tr'))
                rp = o.etree.SubElement(tr, o.q(o.W, 'trPr'))
                o.etree.SubElement(rp, o.q(o.W, 'cantSplit'))
                if row_index == 0 and op.get('header', True):
                    o.etree.SubElement(rp, o.q(o.W, 'tblHeader'))
                for column, text in enumerate(row):
                    cell = o.etree.SubElement(tr, o.q(o.W, 'tc'))
                    cp = o.etree.SubElement(cell, o.q(o.W, 'tcPr'))
                    o.etree.SubElement(cp, o.q(o.W, 'tcW'), attrib={o.q(o.W, 'w'): str(widths[column]), o.q(o.W, 'type'): 'dxa'})
                    if row_index == 0 and op.get('header', True):
                        o.etree.SubElement(cp, o.q(o.W, 'shd'), attrib={o.q(o.W, 'fill'): 'F2F4F7'})
                    p = o.etree.SubElement(cell, o.q(o.W, 'p'))
                    r = o.etree.SubElement(p, o.q(o.W, 'r'))
                    if row_index == 0 and op.get('header', True):
                        rpr = o.etree.SubElement(r, o.q(o.W, 'rPr'))
                        o.etree.SubElement(rpr, o.q(o.W, 'b'))
                    o.etree.SubElement(r, o.q(o.W, 't')).text = text
            # Long tables may break across pages; the header row repeats (tblHeader).
            if op.get('keep_together', len(rows) <= 10):
                paragraphs = list(node.iter(o.q(o.W, 'p')))
                for index, paragraph in enumerate(paragraphs):
                    o.set_para_format(paragraph, {'keep_next': index < len(paragraphs) - 1})
        elif kind == 'insert_image':
            node = o.add_image(parts, root, op, asset_root)
            if op.get('float'):
                rich.float_image(node, op, o)
            else:
                o.set_para_format(node, {'alignment': 'center', 'keep_next': bool(op.get('keep_with_next', True))})
        elif kind == 'insert_table':
            node = rich.table(parts, root, op, o)
        elif kind == 'insert_image_row':
            node = rich.image_row(parts, root, op, asset_root, o)
        elif kind == 'insert_equation':
            node = academic.equation(parts, root, op, o)
        elif kind == 'insert_chart':
            node = academic.chart(parts, root, op, o)
        elif kind == 'insert_caption':
            node = academic.caption(parts, root, op, o)
        elif kind == 'insert_toc':
            node = academic.toc(parts, root, op, o)
        else:
            nodes = o.fragment_nodes([op['xml']], parts)
            node = nodes[0]
            if node.tag != o.q(o.W, 'p') or len(o.ptext(node)) > 3000 or len(list(node.iter(o.q(o.W, 'p')))) != 1:
                raise ValueError('insert_block supports one bounded paragraph; use append_table for tables')
        node.set(BLOCK_ID, block_id)
        after_id = op.get('after_block_id')
        if after_id:
            after = root.xpath('//*[@b:id=$id]', namespaces={'b': BLOCK_NS}, id=after_id)
            if len(after) != 1 or after[0].getparent() != body:
                raise ValueError('Insertion anchor must be one top-level block')
            body.insert(list(body).index(after[0]) + 1, node)
        else:
            ix = next((i for i, b in enumerate(body) if b.tag == o.q(o.W, 'sectPr')), len(body))
            body.insert(ix, node)
    elif kind == 'set_page':
        # Reuse the conservative existing layout implementation.
        updated = o.apply_plan(parts, {'operations': [dict(op, op='set_page')]}, asset_root)
        return updated, ['page-layout'], None
    elif kind == 'set_header_footer':
        rich.header_footer(parts, root, op, o)
    else:
        if target is None:
            raise ValueError('Unknown or ambiguous block_id')
        if kind == 'delete_block':
            target.getparent().remove(target)
        elif kind == 'set_table_format':
            if target.tag != o.q(o.W, 'tbl'):
                raise ValueError('Target must be a table')
            paragraphs = list(target.iter(o.q(o.W, 'p')))
            for index, paragraph in enumerate(paragraphs):
                o.set_para_format(paragraph, {'keep_next': bool(op.get('keep_together', True)) and index < len(paragraphs) - 1})
        elif kind == 'replace_text':
            if target.tag != o.q(o.W, 'p') or not isinstance(op['new'], str) or len(op['new']) > 3000 or '\n' in op['new']:
                raise ValueError('replace_text requires one bounded paragraph')
            o.replace_text_in_paragraph(target, op['old'], op['new'])
        elif kind in ('set_paragraph_style', 'set_paragraph_format'):
            if target.tag != o.q(o.W, 'p'):
                raise ValueError('Target must be a paragraph')
            if kind == 'set_paragraph_style':
                o.require_style(parts, op['style'])
                prop = target.find(o.q(o.W, 'pPr'))
                if prop is None:
                    prop = o.etree.Element(o.q(o.W, 'pPr')); target.insert(0, prop)
                style = prop.find(o.q(o.W, 'pStyle'))
                if style is None:
                    style = o.etree.Element(o.q(o.W, 'pStyle')); prop.insert(0, style)
                style.set(o.q(o.W, 'val'), op['style'])
            else:
                o.set_para_format(target, op)
        elif kind == 'update_toc':
            academic.update_toc(parts, root, target, o)
        elif kind == 'set_table_cell':
            rich.set_cell(parts, root, target, op, o)
        elif kind == 'format_text':
            rich.format_text(root, target, op, o)
        else:
            raise ValueError('Unsupported atomic operation: ' + str(kind))
    unresolved = academic.refresh_fields(parts, root, o)
    academic.normalize_namespaces(root, o)
    parts[o.MAIN] = o.xml_bytes(root)
    return mark_blocks(parts), [block_id], {'unresolved_references': unresolved} if unresolved else None


def _sibling(name):
    spec = importlib.util.spec_from_file_location('docx_skill_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _template_blocks():
    return _sibling('template_blocks')


def _template_styles():
    return _sibling('template_styles')


def _template_manifest(parts, template):
    manifest = _sibling('template_importer').analyze(parts, o, source=str(template))
    sidecar = Path(template).parent / 'manifest.json'
    if sidecar.is_file():
        recorded = json.loads(sidecar.read_text(encoding='utf-8'))
        if isinstance(recorded, dict):
            known = {block['block_id'] for block in manifest.get('blocks') or []}
            for key in ('sections', 'tables'):
                for item in recorded.get(key) or []:
                    block_id = item.get('block_id')
                    if block_id and block_id not in known:
                        raise ValueError(f'Sidecar {key} block_id {block_id} is not in the template')
            manifest['template_id'] = recorded.get('template_id') or manifest['template_id']
            if recorded.get('license'):
                manifest['license'] = recorded['license']
            for key in ('sections', 'tables', 'content_controls'):
                if recorded.get(key):
                    manifest[key] = recorded[key]
    if not manifest.get('blocks'):
        raise ValueError('Template has no paragraphs or tables to index')
    return manifest


def repair_policy():
    path=Path(__file__).resolve().parents[2]/'platform_app'/'office_repair.py'
    if not path.is_file():path=Path(__file__).with_name('office_repair.py')
    spec=importlib.util.spec_from_file_location('docx_office_repair',path)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module
