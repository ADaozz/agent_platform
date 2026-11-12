"""Workflow safety: real snapshots; deterministic rendering only in unit tests."""
import copy
import importlib.util
import json
from pathlib import Path
import sys
from concurrent.futures import ThreadPoolExecutor
import pytest

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('workflow_atomic',ROOT/'docx-ooxml-skill/scripts/atomic_docx.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def plan():
    return dict(version=1,document_id='report',title='Report',page_target=20,sections=[
        dict(id='intro',title='Introduction',requirements='Explain the goal',block_ids=['h1','p1'],styles=['Heading1','Normal']),
        dict(id='analysis',title='Analysis',requirements='Provide evidence',block_ids=['h2','p2','tbl'],tables=['tbl'])])


def request(revision,operation_id,**values):
    return dict(document_id='report',base_revision=revision,operation_id=operation_id,**values)


def fake_render(monkeypatch):
    def render(docx,output,dpi=125):
        import pymupdf as fitz
        pdf=fitz.open();page=pdf.new_page()
        page.insert_text((72,72),'Body line one\nBody line two')
        pdf.save(output/'preview.pdf');page.get_pixmap().save(output/'page-001.png');pdf.close()
    monkeypatch.setattr(a.o,'run_render',render)


@pytest.fixture
def store(tmp_path,monkeypatch):
    fake_render(monkeypatch)
    result=a.DocumentStore(tmp_path/'report.docx');result.init('report',design='academic')
    result.save_plan(request(0,'plan-1',plan=plan()))
    return result


def section(revision=1):
    return request(revision,'section-1',section_id='intro',operations=[
        dict(type='append_paragraph',block_id='h1',style='Heading1',text='Introduction'),
        dict(type='append_paragraph',block_id='p1',text='Goal and context')])


def test_section_commits_once_replays_and_previews_once(store,monkeypatch):
    calls=[];original=store.render_snapshot
    monkeypatch.setattr(store,'render_snapshot',lambda rev:(calls.append(rev),original(rev))[1])
    result=store.apply_section(section())
    assert result['revision']==2 and result['operation_count']==2
    assert store.status()['revision']==2
    assert calls==[2]
    assert store.apply_section(section())==result
    assert calls==[2]
    assert len([e for e in store.events() if e['type']=='document_revision' and e['operation_id']=='section-1'])==1
    bad=section();bad['operations'][1]['text']='Changed'
    with pytest.raises(ValueError,match='Operation ID reused'):store.apply_section(bad)


def test_mid_section_failure_does_not_change_bytes_revision_or_events(store):
    before=store.path.read_bytes();events=store.events();state=store.status()
    bad=section();bad['operations'][1]['type']='unsupported'
    with pytest.raises(ValueError):store.apply_section(bad)
    assert store.path.read_bytes()==before
    assert store.status()['revision']==state['revision'] and store.events()==events
    assert store.status()['sections']==state['sections']


def test_budget_conflict_and_scope_checks(store):
    bad=section();bad['operations']*=41
    with pytest.raises(ValueError,match='count'):store.apply_section(bad)
    bad=section();bad['operations'][1]['block_id']='p2'
    with pytest.raises(ValueError,match='planned section'):store.apply_section(bad)
    bad=section();bad['operations'][0]['after_block_id']='p2'
    with pytest.raises(ValueError,match='Cross-section'):store.apply_section(bad)
    with pytest.raises(ValueError,match='Revision conflict'):store.apply_section(section(0))
    bad=section();bad['operations']=[dict(type='insert_image',block_id='p1',path='../escape.png')]
    with pytest.raises(ValueError,match='resource path'):store.apply_section(bad,store.path.parent)
    assert store.status()['revision']==1


def test_plan_correction_preserves_content_and_unaffected_sections(store):
    store.apply_section(section());before=store.path.read_bytes();old=store.status()['sections']['intro']
    corrected=plan();corrected['sections'][1]['requirements']='Use revised evidence'
    result=store.save_plan(request(2,'plan-2',plan=corrected))
    assert result['affected_sections']==['analysis']
    assert store.path.read_bytes()==before
    assert store.status()['sections']['intro']==old
    assert store.status()['sections']['analysis']['status']=='needs_review'
    store.restore(1,3,'restore-plan')
    assert store.status()['document_plan']==plan()


def test_concurrent_sections_only_one_commits(store):
    def apply(number):
        payload=section();payload['operation_id']=f'concurrent-{number}'
        try:return store.apply_section(payload)['revision']
        except ValueError:return None
    with ThreadPoolExecutor(max_workers=2) as pool:results=list(pool.map(apply,range(2)))
    assert results.count(2)==1
    assert store.status()['revision']==2


def test_failed_render_leaves_committed_section_recoverable(store,monkeypatch):
    monkeypatch.setattr(a.o,'run_render',lambda *args:(_ for _ in ()).throw(RuntimeError('render unavailable')))
    committed=store.apply_section(section())
    assert committed['revision']==2
    assert store.status()['gate']=='failed' and store.status()['render_error']
    fake_render(monkeypatch)
    assert store.check_document()['layout_passed']


def test_deterministic_local_repair_then_check(store):
    store.apply_section(section())
    store.apply_one(request(2,'break-heading',operation=dict(type='set_paragraph_format',block_id='h1',keep_next=False)))
    store.check_document()
    # Keep a single-section plan for the completed delivery case.
    completed=plan();completed['sections']=completed['sections'][:1]
    store.save_plan(request(3,'complete-plan',plan=completed))
    check=store.check_document(final=True)
    targets=[t for t in check['repair_targets'] if t['deterministic']]
    assert [t['block_id'] for t in targets]==['h1']
    text_before={b['block_id']:b['text'] for b in store.status()['blocks']}
    result=store.repair_document(4,'repair-1')
    assert result['revision']==5 and result['recheck']['passed']
    assert text_before=={b['block_id']:b['text'] for b in store.status()['blocks']}
    assert store.repair_document(4,'repair-1')['revision']==5
    assert store.finalize(5)['status']=='finalized'


def test_missing_planned_blocks_are_reported_and_block_delivery(store):
    store.apply_section(section())
    check=store.check_document(final=True)
    assert {t['block_id'] for t in check['repair_targets'] if t['code']=='missing_planned_block'}=={'h2','p2','tbl'}
    assert store.repair_document(2,'nothing')['status']=='unrepairable'
    with pytest.raises(ValueError):store.finalize(2)


def test_design_template_priority_and_native_styles(tmp_path):
    from docx import Document
    template=tmp_path/'template.docx';doc=Document();doc.add_paragraph('Preserve');doc.save(template)
    template_parts=a.o.read_parts(template)
    store=a.DocumentStore(tmp_path/'templated.docx');store.init('templated',template,design='nonexistent')
    assert a.o.read_parts(store.path)['word/styles.xml']==template_parts['word/styles.xml']
    assert store.status()['selected_design'] is None
    for style in a._sibling('document_design').list_styles():
        target=a.DocumentStore(tmp_path/(style['id']+'.docx'));target.init(style['id'],design=style['id'])
        parts=a.o.read_parts(target.path)
        assert a.o.validate_parts(parts)['ok']
        assert b'DocumentTable' in parts['word/styles.xml']


@pytest.mark.parametrize('mutation',[
    lambda p:p.update(version=2),lambda p:p['sections'].append(p['sections'][0]),
    lambda p:p['sections'][0].update(citations=['missing']),
    lambda p:p['sections'][1].update(block_ids=['p1']),
    lambda p:p['sections'][0].update(figures=['unplanned'])])
def test_invalid_plans_rejected(mutation):
    value=copy.deepcopy(plan());mutation(value)
    with pytest.raises(ValueError):a._sibling('document_plan').validate(value)


def test_legacy_documents_keep_page_review_instead_of_agent_submission(store):
    store.apply_section(section())
    assert store.metadata()['quality_contract']==1
    with pytest.raises(ValueError,match='review-page'):store.review_images()
    with pytest.raises(ValueError,match='review-page'):
        store.submit_review(dict(revision=store.status()['revision'],pages=[dict(page=1,unavailable='not checked')]))
    assert not store.metadata().get('aesthetic_reviews')


def test_section_publish_crash_recovers_metadata_and_replay(store,monkeypatch):
    real=a.publish
    def crash(*args):raise OSError('publish interrupted')
    monkeypatch.setattr(a,'publish',crash)
    with pytest.raises(OSError,match='interrupted'):store.apply_section(section())
    monkeypatch.setattr(a,'publish',real)
    reopened=a.DocumentStore(store.path)
    state=reopened.status()
    assert state['revision']==2 and state['gate']=='checkpoint'
    assert state['sections']['intro']['status']=='generated'
    assert reopened.path.read_bytes()==reopened.snapshot(2)
    assert reopened.apply_section(section())['revision']==2


def test_host_adapter_runs_no_visual_review_worker(store,tmp_path):
    spec=importlib.util.spec_from_file_location('docx_review_host_test',ROOT/'docx-ooxml-skill/platform_adapter.py')
    adapter=importlib.util.module_from_spec(spec);spec.loader.exec_module(adapter)
    service=adapter.Documents(store.path.parent,host=dict(private_root=tmp_path/'host'))
    assert not hasattr(service,'reviews')
    store.apply_section(section());service.sync()
    assert not store.metadata().get('aesthetic_reviews') and not (tmp_path/'host').exists()
    service.close()


def test_complex_template_section_edit_preserves_other_parts_and_rejects_lossy_edit(tmp_path,monkeypatch):
    from docx import Document
    from PIL import Image
    fake_render(monkeypatch)
    template=tmp_path/'source.docx';doc=Document()
    doc.sections[0].header.paragraphs[0].text='Unchanged header'
    doc.add_paragraph('Editable slot')
    mixed=doc.add_paragraph();mixed.add_run('Mixed ').bold=True;mixed.add_run('format').italic=True
    nested=doc.add_table(rows=1,cols=1).cell(0,0);nested.text='Nested container';nested.add_table(rows=1,cols=2).cell(0,0).text='Nested content'
    image=tmp_path/'image.png';Image.new('RGB',(30,20),'blue').save(image);doc.add_picture(str(image));doc.save(template)
    store=a.DocumentStore(tmp_path/'target.docx');store.init('report',template)
    blocks={b['text']:b['block_id'] for b in store.status()['blocks']}
    slot=blocks['Editable slot'];mixed_id=blocks['Mixed format']
    value=dict(version=1,document_id='report',title='Template edit',sections=[dict(id='edit',title='Edit',requirements='Local replacement',block_ids=[slot,mixed_id])])
    store.save_plan(request(0,'template-plan',plan=value));before=a.o.read_parts(store.path)
    payload=request(1,'edit-template',section_id='edit',operations=[dict(type='replace_text',block_id=slot,old='Editable',new='Updated')])
    store.apply_section(payload)
    after=a.o.read_parts(store.path)
    assert all(after[name]==data for name,data in before.items() if name!=a.o.MAIN)
    # A rejected rewrite after an otherwise valid earlier operation rolls everything back.
    original=store.path.read_bytes();revision=store.status()['revision']
    payload=request(revision,'lossy',section_id='edit',operations=[dict(type='replace_text',block_id=slot,old='Updated',new='Discarded'),dict(type='slot.fill',block_id=mixed_id,text='flatten')])
    with pytest.raises(ValueError):store.apply_section(payload)
    assert store.path.read_bytes()==original and store.status()['revision']==revision


def test_long_table_repair_is_local_and_preserves_content(store):
    # A deliberately malformed existing long table, as encountered in templates.
    store.apply_section(section())
    request2=request(2,'analysis',section_id='analysis',operations=[
        dict(type='append_paragraph',block_id='h2',style='Heading1',text='Analysis'),
        dict(type='append_paragraph',block_id='p2',text='Evidence'),
        dict(type='append_table',block_id='tbl',header=False,keep_together=True,rows=[['Metric','Value']]+[[f'Metric {i}',str(i)] for i in range(15)])])
    store.apply_section(request2)
    check=store.check_document(final=True)
    assert any(t['code']=='long_table_pagination' and t['block_id']=='tbl' for t in check['repair_targets'])
    before={b['block_id']:b['text'] for b in store.status()['blocks']}
    repaired=store.repair_document(3,'table-repair')
    assert repaired['revision']==4 and repaired['recheck']['passed']
    assert before=={b['block_id']:b['text'] for b in store.status()['blocks']}


def test_unresolved_reference_and_plan_resource_mismatch_are_reported(store):
    value=plan();value['sections']=value['sections'][:1];value['sections'][0]['equations']=['p1']
    store.save_plan(request(1,'new-inventory',plan=value))
    payload=section(2);payload['operations'][1]['text']='See {{ref:missing-reference}}'
    store.apply_section(payload)
    check=store.check_document(final=True)
    assert any(t['code']=='unresolved_reference' and t['block_id']=='p1' for t in check['repair_targets'])
    assert any(t['code']=='planned_resource_type' and t['block_id']=='p1' for t in check['repair_targets'])
    assert store.repair_document(3,'report-only')['status']=='unrepairable'


def test_resource_and_character_budgets_reject_before_commit(store,tmp_path):
    (tmp_path/'oversized.png').write_bytes(b'x'*(20*1024*1024+1))
    payload=section();payload['operations']=[dict(type='insert_image',block_id='p1',path='oversized.png')]
    with pytest.raises(ValueError,match='resource budget'):store.apply_section(payload,tmp_path)
    payload=section();payload['operations']=[dict(type='append_paragraph',block_id='p1',text='x'*120001)]
    with pytest.raises(ValueError,match='character budget'):store.apply_section(payload,tmp_path)
    assert store.status()['revision']==1


def test_automatic_table_repair_refuses_complex_template_structure(tmp_path):
    from docx import Document
    from types import SimpleNamespace
    template=tmp_path/'merged.docx';doc=Document();table=doc.add_table(rows=16,cols=2)
    table.cell(0,0).merge(table.cell(0,1)).text='Merged heading'
    for i in range(1,16):table.cell(i,0).text=f'Row {i}'
    doc.save(template)
    store=a.DocumentStore(tmp_path/'preserved.docx');store.init('report',template)
    parts=a.o.read_parts(store.path)
    issues=a._sibling('document_workflow').inspect_parts(parts,SimpleNamespace(o=a.o,BLOCK_ID=a.BLOCK_ID))
    target=next(issue for issue in issues if issue['code']=='long_table_pagination')
    assert target['block_id'] and target['deterministic'] is False and target['operation'] is None
    assert 'manual review' in target['detail']



def test_restore_chains_preserve_the_plan_and_original_review_contract(store):
    store.apply_section(section())
    corrected=plan();corrected['sections'][1]['requirements']='New evidence'
    store.save_plan(request(2,'plan-update',plan=corrected))
    store.restore(1,3,'restore-original-plan')
    assert store.status()['document_plan']==plan()
    assert not store.status().get('workflow_version')
    store.checkpoint()
    store.apply_one(request(4,'legacy-after-restore',operation=dict(type='append_paragraph',block_id='legacy',text='Preserved legacy edit')))
    store.restore(5,5,'restore-a-restored-branch')
    assert store.status()['document_plan']==plan()
    assert not store.status().get('workflow_version')
    store.restore(2,6,'restore-section-workflow')
    assert store.status()['document_plan']==plan()
    assert store.status()['workflow_version']==1


def test_metadata_polling_avoids_unpacking_and_preserves_external_conflicts(store,monkeypatch):
    def unexpected(*args,**kwargs):raise AssertionError('Metadata unpacked the document')
    monkeypatch.setattr(a.o,'read_parts',unexpected)
    assert store.metadata()['revision']==1
    assert store.metadata(external=True)['external_conflict'] is False
    store.path.write_bytes(store.path.read_bytes()+b'external edit')
    assert store.metadata(external=True)['external_conflict'] is True
