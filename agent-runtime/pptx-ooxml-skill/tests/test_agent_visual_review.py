"""Main-Agent visual review: real renders in, schema-checked and revision-safe answers out, never a silent pass."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
pytestmark = pytest.mark.skipif(not shutil.which('libreoffice'), reason='LibreOffice Impress required')

spec = importlib.util.spec_from_file_location('ppt_agent_review_adapter', ROOT / 'pptx-ooxml-skill' / 'platform_adapter.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)
engine = adapter.engine
review = engine.agent_review
PNG = b'\x89PNG\r\n\x1a\n'


def checks(names=review.DIMENSIONS, note='标题在左上方，正文三点左对齐，右侧留白给图表'):
    return {key: dict(verdict='ok', evidence=f'{label}：{note}') for key, label in names.items()}


def answer(status='pass', issues=(), **extra):
    return dict(status=status, summary='逐项核对截图', checks=extra.pop('checks', checks()), issues=list(issues), **extra)


def issue(number=1, severity='major', confidence='high', element_ids=('title',), category='legibility', **extra):
    return dict(id=f'visual-{number:03d}', category=category, severity=severity, element_ids=list(element_ids), region=[.05, .05, .5, .12],
        observation='标题文字与背景对比不足', reason='投影时难以辨认', suggestion='将标题改为深色文字', confidence=confidence, **extra)


class Harness:
    def __init__(self, tmp_path):
        self.root = tmp_path / 'files'
        self.root.mkdir(parents=True)
        self.events = []
        self.service = adapter.create_service(self.root, self.events.append, temporary_root=tmp_path / 'renders', host=dict(private_root=tmp_path / 'private'))
        self.path = self.root / 'deck.pptx'
        self.store = self.service.store(self.path)
        self.store.init('deck')

    def op(self, kind, sid='s1', **kwargs):
        state = self.store.status()
        return self.store.apply_one(dict(presentation_id='deck', operation_id=f'op-{state["revision"] + 1}', base_revision=state['revision'],
            slide_id=sid, operation=kind, **kwargs))

    def slide(self, sid='s1', title='AI Agent 平台建设方案', **check):
        self.op('slide.add', sid=sid, layout='title_body')
        self.op('element.add_text', sid=sid, element=dict(id='title', anchor='title', text=title))
        return self.check(sid, **check)

    def check(self, sid='s1', **kwargs):
        result = self.store.check_slide(sid, '逐字核对标题', kwargs.get('intent'), kwargs.get('constraints'))
        self.service.sync()
        return result

    def submit(self, slides=(), deck=None):
        request = dict(revision=self.store.status()['revision'], slides=[dict(slide_id=sid, review=value) for sid, value in slides])
        if deck is not None:
            request['deck'] = deck
        result = self.store.submit_review(request)
        self.service.sync()
        return result

    def summary(self, sid='s1'):
        return self.store.review_status(sid)['slides'][0]

    def verification(self):
        deadline = time.time() + 60
        while time.time() < deadline:
            self.service.sync()
            found = [e for e in self.events if e.get('type') == 'presentation_finalize_verification']
            if found:
                return found[-1]
            time.sleep(.2)
        raise AssertionError('finalize verification did not run')

    def close(self):
        self.service.close()


@pytest.fixture
def harness(tmp_path):
    made = []

    def make():
        made.append(Harness(tmp_path / f'h{len(made)}'))
        return made[-1]
    yield make
    for item in made:
        item.close()


def test_review_images_returns_the_real_render_and_structured_context(harness):
    h = harness()
    h.slide(intent='开篇点题', constraints=['保留左对齐的标题'])
    assert h.summary()['aesthetic_review']['status'] == 'pending'
    assert h.summary()['aesthetic_review']['reason'] == 'awaiting_agent_review'
    result = h.store.review_images()
    [item] = result['slides']
    assert item['slide_id'] == 's1' and item['reviewable'] and item['status'] == 'pending'
    image = Path(item['image'])
    assert image.is_absolute() and image.read_bytes()[:8] == PNG
    assert set(review.DIMENSIONS) == set(result['guidance']['dimensions']) and 'read_file' in result['guidance']['slide']
    context = json.loads(Path(result['context_file']).read_text())
    page = context['slides'][0]
    assert page['page']['purpose'] == '开篇点题' and page['page']['user_constraints'] == ['保留左对齐的标题']
    assert {e['id'] for e in page['elements']} == {'title'} and page['image'] == item['image']
    assert result['deck'] is None  # A one-slide deck has no deck review.
    assert 'submit-review' in result['next_action']


def test_host_never_calls_a_model(harness):
    h = harness()
    assert not hasattr(h.service.reviews, 'model') and not hasattr(adapter, 'vision')
    h.slide()
    time.sleep(.5)
    h.service.sync()
    assert h.summary()['aesthetic_review']['status'] == 'pending'


def test_submitted_review_is_applied_and_recorded_on_the_host(harness):
    h = harness()
    h.slide()
    result = h.submit([('s1', answer())])
    assert result['slides'][0]['applied'] and result['slides'][0]['status'] == 'passed'
    summary = h.summary()
    aesthetic = summary['aesthetic_review']
    assert aesthetic['status'] == 'passed' and summary['status'] == 'passed'
    assert aesthetic['reviewer'] == 'main_agent' and aesthetic['prompt_version'] == review.GUIDANCE_VERSION
    record = h.service.reviews.ledger.get(aesthetic['review_id'])
    assert record and record['slide_id'] == 's1' and record['status'] == 'passed' and record['presentation_id'] == 'deck'
    png = Path(h.store.review_images()['slides'][0]['image']).read_bytes()
    assert record['pixel_sha256'] == review.pixel_sha256(png)


@pytest.mark.parametrize('submitted,expected', [
    (answer(score=98), 'passed'),
    (answer('pass', [issue(confidence='low')]), 'uncertain'),
    (answer('pass', [issue(needs_verification=True, category='diagram_semantics')]), 'uncertain'),
    (answer('pass', [issue()]), 'failed'),
    (answer('fail'), 'uncertain'),
    (answer('uncertain'), 'uncertain'),
    (answer('pass', [issue(severity='minor', category='spacing')]), 'passed'),
])
def test_status_is_derived_from_evidence_not_from_the_submitted_verdict(harness, submitted, expected):
    h = harness()
    h.slide()
    h.submit([('s1', submitted)])
    assert h.summary()['aesthetic_review']['status'] == expected


def test_answers_outside_the_structure_are_rejected_and_record_nothing(harness):
    h = harness()
    h.slide()
    wrong_verdict = answer()
    wrong_verdict['checks']['decoration']['verdict'] = 'minor'
    missing = answer(checks={'composition': dict(verdict='ok', evidence='居中')})
    bad_region = answer('fail', [dict(issue(), region=[.5, .5, 1.5, .1])])
    bad_id = answer('fail', [dict(issue(), id='issue-1')])
    for submitted in (dict(status='pass'), wrong_verdict, missing, bad_region, bad_id, '看起来很专业'):
        with pytest.raises(ValueError, match='nothing recorded'):
            h.submit([('s1', submitted)])
    assert h.summary()['aesthetic_review']['status'] == 'pending'
    assert not any(e.get('type') == 'presentation_aesthetic_review' for e in h.events)


def test_one_invalid_entry_rejects_the_whole_batch(harness):
    h = harness()
    h.slide('s1')
    h.slide('s2', title='第二页')
    with pytest.raises(ValueError, match='s2'):
        h.submit([('s1', answer()), ('s2', dict(status='pass'))])
    assert h.summary('s1')['aesthetic_review']['status'] == 'pending'


def test_invented_element_ids_are_dropped_and_reported(harness):
    h = harness()
    h.slide()
    h.submit([('s1', answer('fail', [issue(element_ids=('ghost-01', 'title'))]))])
    item = h.summary()['aesthetic_review']['issues'][0]
    assert item['element_ids'] == ['title'] and item['unmapped_element_ids'] == ['ghost-01']


def test_agent_that_cannot_view_images_reports_unavailable_never_a_pass(harness):
    h = harness()
    h.slide()
    revision = h.store.status()['revision']
    h.store.submit_review(dict(revision=revision, slides=[dict(slide_id='s1', unavailable='当前模型不支持图片输入')]))
    summary = h.summary()
    assert summary['aesthetic_review']['status'] == 'unavailable'
    assert summary['aesthetic_review']['error']['code'] == 'agent_cannot_inspect'
    assert 'Do not claim visual acceptance' in summary['next_action']
    assert h.store.finalize(revision)['aesthetics']['s1']['status'] == 'unavailable'


def test_review_of_an_old_revision_is_rejected(harness):
    h = harness()
    h.slide()
    old = h.store.status()['revision']
    h.op('element.update', element=dict(id='title', text='修改后的标题'))
    with pytest.raises(ValueError, match='Revision conflict'):
        h.store.submit_review(dict(revision=old, slides=[dict(slide_id='s1', review=answer())]))
    current = h.store.review_images()['slides'][0]
    assert not current['reviewable'] and 'check-deck' in current['reason']
    with pytest.raises(ValueError, match='nothing recorded'):
        h.submit([('s1', answer())])
    h.check()
    h.submit([('s1', answer())])
    assert h.summary()['aesthetic_review']['status'] == 'passed'


def test_resubmission_replaces_the_previous_review_of_the_same_check(harness):
    h = harness()
    h.slide()
    h.submit([('s1', answer('fail', [issue()]))])
    first = h.summary()['aesthetic_review']['review_id']
    h.submit([('s1', answer())])
    second = h.summary()['aesthetic_review']
    assert second['status'] == 'passed' and second['review_id'] != first


def test_even_critical_visual_findings_are_advice_without_automatic_repairs(harness):
    h = harness()
    h.slide()
    before = h.store.path.read_bytes()
    h.submit([('s1', answer('fail', [issue(severity='critical')]))])
    summary = h.summary()
    assert summary['aesthetic_review']['status'] == 'failed' and summary['status'] == 'needs_attention'
    assert summary['aesthetic_review']['auto_repair'] is False and summary['aesthetic_review']['advisory_only'] is True
    assert 'change nothing unless asked' in summary['next_action']
    assert h.store.path.read_bytes() == before
    event = h.store.finalize(h.store.status()['revision'])
    assert event['outstanding_critical'] == {'s1': ['visual-001']}


def test_dismissal_keeps_the_verdict_without_implicit_acceptance(harness):
    h = harness()
    h.slide()
    h.submit([('s1', answer('fail', [issue(severity='critical')]))])
    revision = h.store.status()['revision']
    h.service.dismiss_issues('deck', revision, ['visual-001'], slide_id='s1')
    result = h.summary()
    assert result['effective_aesthetic'] == 'failed'
    assert result['aesthetic_review']['issues'][0]['dismissed'] and result['critical_issues'] == []


def test_submitted_verdicts_pass_host_verification(harness):
    h = harness()
    h.slide()
    h.submit([('s1', answer())])
    h.store.finalize(h.store.status()['revision'])
    verification = h.verification()
    assert verification['finalize_verified'], verification


def test_forged_acceptance_in_sandbox_state_fails_host_verification(harness):
    h = harness()
    h.slide()
    with h.store.locked() as (c, state):
        item = state['reviews']['s1']
        item['aesthetic_review'] = dict(status='passed', review_id='forged', reviewer='main_agent')
        item['status'] = 'passed'
        h.store.save_state(c, state)
        c.commit()
    h.store.finalize(h.store.status()['revision'])
    verification = h.verification()
    assert not verification['finalize_verified'] and 's1' in verification['verification_problems'][0]


def deck_review(issues=()):
    return dict(status='fail' if issues else 'pass', summary='整套审查', checks=checks(review.DECK_CATEGORIES, '第 1-3 页统一深蓝标题'), issues=list(issues))


def deck_issue(number, slides, category='repetition'):
    return dict(id=f'deck-{number:03d}', category=category, severity='major', slides=slides, observation='第 2、3 页都是左上标题加大片留白',
        reason='相邻页节奏单调', suggestion='第 3 页改用数据版式', confidence='high')


def test_deck_review_names_specific_pages_and_rejects_invented_ones(harness):
    h = harness()
    for index in range(1, 4):
        h.op('slide.add', sid=f's{index}', layout='title_body')
        h.op('element.add_text', sid=f's{index}', element=dict(id='title', anchor='title', text=f'第 {index} 页'))
    result = h.store.check_deck({f's{index}': '逐字核对标题' for index in range(1, 4)})
    assert result['status'] == 'passed' and 'review-images' in result['next_action']
    images = h.store.review_images()
    assert images['deck']['reviewable'] and Path(images['deck']['sheet']).read_bytes()[:8] == PNG
    assert [item['page'] for item in images['slides']] == [1, 2, 3]
    context = json.loads(Path(images['context_file']).read_text())
    assert [s['page'] for s in context['deck']['slides']] == [1, 2, 3]
    h.submit([(f's{index}', answer()) for index in range(1, 4)], deck=dict(review=deck_review([deck_issue(1, [2, 3]), deck_issue(2, [4], 'design_system')])))
    deck = h.store.review_status()['deck_review']
    assert deck['status'] == 'failed' and deck['reviewer'] == 'main_agent'
    assert [i['slides'] for i in deck['issues']] == [[2, 3]] and deck['issues'][0]['slide_ids'] == ['s2', 's3']
    assert deck['rejected_issues'][0]['id'] == 'deck-002'
    assert h.service.reviews.ledger.get(deck['review_id'])['status'] == 'failed'
    with pytest.raises(ValueError, match='no pending deck review'):
        h.submit(deck=dict(review=deck_review()))


def test_deck_review_of_a_changed_deck_is_stale(harness):
    h = harness()
    for index in range(1, 3):
        h.slide(f's{index}', title=f'第 {index} 页')
    requested = h.store.request_deck_review(h.store.status()['revision'])
    request_id = requested['deck_review']['request_id']
    h.op('element.adjust', sid='s1', element={'id': 'title', 'dx_in': 0.15})
    assert h.store.status()['deck_review']['status'] == 'stale'
    assert h.store.record_deck_review(request_id, dict(status='passed', summary='late')) == dict(applied=False, reason='stale')
    with pytest.raises(ValueError, match='no pending deck review'):
        h.submit(deck=dict(review=deck_review()))


def test_unsupported_chart_preview_cannot_be_reviewed(harness):
    h = harness()
    h.op('slide.add', layout='title_body')
    h.op('element.add_chart', element=dict(id='waterfall', geometry=dict(x=.1, y=.25, w=.8, h=.6),
        chart=dict(type='waterfall', categories=['Start', 'Change', 'End'], series=[dict(name='Cash', values=[100, -20, 80])], totals=[0, 2])))
    result = h.check()
    assert result['review']['aesthetic_review']['error']['code'] == 'unsupported_chart_renderer'
    item = h.store.review_images()['slides'][0]
    assert not item['reviewable'] and 'PowerPoint' in item['reason']
    with pytest.raises(ValueError, match='PowerPoint'):
        h.submit([('s1', answer())])


def test_changed_page_exposes_previous_review_without_accepting_it(harness):
    h = harness()
    h.slide()
    h.submit([('s1', answer())])
    previous = h.summary()['aesthetic_review']['review_id']
    h.op('element.update', element={'id': 'title', 'text': '更新后的汇报标题'})
    slide = h.store.status()['manifest']['slides'][0]
    assert slide['review']['status'] == 'writing'
    assert slide['previous_review']['aesthetic_review']['review_id'] == previous
    h.store.check_slide('s1', '标题已更新')
    slide = h.store.status()['manifest']['slides'][0]
    assert slide['review']['aesthetic_review']['status'] == 'pending'


def test_cli_review_images_and_submit_review(tmp_path):
    h = Harness(tmp_path)
    try:
        h.slide()
        script = ROOT / 'pptx-ooxml-skill' / 'scripts' / 'office_pptx.py'
        run = lambda *args: subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True, timeout=180)
        listed = run('review-images', str(h.path))
        assert listed.returncode == 0, listed.stderr
        payload = json.loads(listed.stdout)
        request = tmp_path / 'review.json'
        request.write_text(json.dumps(dict(revision=payload['revision'], slides=[dict(slide_id='s1', review=answer())]), ensure_ascii=False))
        submitted = run('submit-review', str(h.path), '--request', str(request))
        assert submitted.returncode == 0, submitted.stderr
        assert json.loads(submitted.stdout)['slides'][0]['status'] == 'passed'
        request.write_text(json.dumps(dict(revision=payload['revision'], slides=[dict(slide_id='s1', review=dict(status='pass'))])))
        rejected = run('submit-review', str(h.path), '--request', str(request))
        assert rejected.returncode == 1 and 'nothing recorded' in rejected.stderr
    finally:
        h.close()


def test_feature_snapshot_ships_the_review_module_without_host_files(tmp_path):
    from platform_app import format_plugins
    format_plugins.snapshot_skills(tmp_path)
    copied = tmp_path / 'pptx-ooxml-author'
    assert (copied / 'scripts' / 'office_pptx.py').is_file() and (copied / 'scripts' / 'agent_review.py').is_file()
    assert not (copied / 'platform_adapter.py').exists() and not (copied / 'vision_review_service.py').exists()
