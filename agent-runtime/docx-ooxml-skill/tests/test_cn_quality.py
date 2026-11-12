"""Actual OOXML/LibreOffice regressions for mandatory research-document acceptance."""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import time
import threading
import pytest

ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
spec=importlib.util.spec_from_file_location('cn_quality_atomic',ROOT/'docx-ooxml-skill/scripts/atomic_docx.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)


def envelope(store,name,**data):
    s=store.metadata();return dict(document_id=s['document_id'],base_revision=s['revision'],operation_id=name,**data)


def make_store(tmp_path,sections,design='cn-thesis-general'):
    store=a.DocumentStore(tmp_path/'report.docx');store.init('report',design=design)
    plan=dict(version=1,document_id='report',title='科研报告',sections=sections)
    store.save_plan(envelope(store,'plan',plan=plan));return store


def section(identity,blocks,kind='body',**extra):
    return dict(id=identity,title=identity,requirements='检查组件与排版',block_ids=blocks,kind=kind,**extra)


@pytest.mark.parametrize('identity',['cn-thesis-general','cn-engineering-thesis','cn-journal-paper','cn-research-report'])
def test_cn_designs_select_apply_and_define_separate_fonts(tmp_path,identity):
    store=a.DocumentStore(tmp_path/(identity+'.docx'));store.init('report',design=identity)
    parts=a.o.read_parts(store.path);styles=a.o.parse_xml(parts['word/styles.xml'])
    normal=styles.xpath('//w:style[@w:styleId="Normal"]',namespaces=a.o.NS)[0]
    assert normal.xpath('string(./w:rPr/w:rFonts/@w:eastAsia)',namespaces=a.o.NS)=='Noto Serif CJK SC'
    assert normal.xpath('string(./w:rPr/w:rFonts/@w:ascii)',namespaces=a.o.NS)=='Liberation Serif'
    config=store.metadata()['selected_design']
    assert config['sources'] and {'cover','abstract','toc','equation','citations','references','pagination'}<=config['components'].keys()
    assert store.metadata()['quality_contract']==2


@pytest.mark.skipif(not shutil.which('libreoffice'),reason='LibreOffice required')
def test_cover_date_overflow_is_detected_and_locally_repaired(tmp_path):
    store=make_store(tmp_path,[section('cover',['title','date'],'cover')])
    store.apply_section(envelope(store,'cover',section_id='cover',operations=[
        dict(type='append_paragraph',block_id='title',style='CoverTitle',text='科研项目总结报告'),
        dict(type='set_paragraph_format',block_id='title',space_after_twips=14000),
        dict(type='append_paragraph',block_id='date',style='CoverDate',text='2026 年 11 月 11 日')]))
    check=store.check_document(final=True,auto_repair=False)
    assert any(t['code']=='cover_overflow' and t['block_id']=='date' for t in check['repair_targets'])
    before={b['block_id']:b['text'] for b in store.status()['blocks']}
    result=store.repair_document(check['revision'],'cover-repair')
    assert result['recheck']['passed'],result['recheck']['repair_targets']
    assert len(result['recheck']['pages'])==1
    assert before=={b['block_id']:b['text'] for b in store.status()['blocks']}
    assert result['repair_attempts']>=1 and result['stop_reason'] is None


@pytest.mark.skipif(not shutil.which('libreoffice'),reason='LibreOffice required')
def test_native_toc_empty_page_cache_is_repaired_against_real_pdf(tmp_path):
    store=make_store(tmp_path,[section('toc',['toc'],'toc'),section('body',['h','p'])])
    store.apply_section(envelope(store,'toc',section_id='toc',operations=[dict(type='insert_toc',block_id='toc',levels=3)]))
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 研究方法'),dict(type='append_paragraph',block_id='p',text='正文介绍研究对象、可追踪的实验方法与检查结果。')]))
    check=store.check_document(final=True,auto_repair=False)
    assert any(t['code']=='toc_page_results' for t in check['repair_targets'])
    result=store.repair_document(check['revision'],'toc-repair')
    assert result['recheck']['passed'],result['recheck']['repair_targets']
    root=a.o.parse_xml(a.o.read_parts(store.path)[a.o.MAIN])
    assert root.xpath('//w:fldSimple[contains(@w:instr,"PAGEREF")]//w:t[text()="1"]',namespaces=a.o.NS)


def test_leader_dots_without_page_fields_cannot_pass(tmp_path):
    store=make_store(tmp_path,[section('toc',['fake'],'toc')])
    store.apply_section(envelope(store,'fake',section_id='toc',operations=[dict(type='append_paragraph',block_id='fake',style='TOC1',text='研究方法 ............')]))
    result=store.check_document(final=True)
    assert not result['passed']
    assert any(t['code']=='toc_page_numbers_missing' for t in result['repair_targets'])
    with pytest.raises(ValueError):store.finalize(store.metadata()['revision'])
    assert store.path.exists() and not store.metadata()['finalized']


def test_wrong_chinese_direct_font_and_size_are_reported(tmp_path):
    store=make_store(tmp_path,[section('body',['p'])])
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='p',runs=[dict(text='中文科研正文',font='Noto Sans CJK SC',size=10)])]))
    result=store.check_document(final=True,auto_repair=False)
    assert any(t['code']=='style_deviation' and t['block_id']=='p' for t in result['repair_targets'])
    repair=store.repair_document(result['revision'],'do-not-shrink')
    assert repair['exhausted'] and repair['repair_attempts']==0


def test_collision_detection_and_normal_wrapping_geometry(tmp_path):
    import pymupdf as fitz
    from PIL import Image
    Image.new('RGB',(100,100),'blue').save(tmp_path/'figure.png')
    parts=a.o.default_package()
    parts,_,_=a.mutate(parts,dict(type='append_paragraph',block_id='text',text='Independent text box'),tmp_path)
    parts,_,_=a.mutate(parts,dict(type='insert_image',block_id='image',path='figure.png',width_cm=3,float='left'),tmp_path)
    pdf=fitz.open();page=pdf.new_page();page.insert_image(fitz.Rect(72,72,172,172),filename=str(tmp_path/'figure.png'));page.insert_text((80,110),'Independent text box')
    result=a._sibling('layout_review').inspect(parts,pdf,a.o,a.BLOCK_ID)
    collisions=[t for t in result['findings'] if t['code']=='text_image_collision']
    assert collisions and collisions[0]['block_id']=='text' and collisions[0]['detail']['image_block_id']=='image'
    normal=fitz.open();p=normal.new_page();p.insert_image(fitz.Rect(72,72,172,172),filename=str(tmp_path/'figure.png'));p.insert_text((190,110),'Independent text box')
    result=a._sibling('layout_review').inspect(parts,normal,a.o,a.BLOCK_ID)
    assert not any(t['code'].endswith('collision') for t in result['findings'])


def test_delivery_has_three_independent_states_and_never_accepts_unknown():
    delivery=a._sibling('quality_status').delivery
    state=dict(document_id='d',revision=4,quality_contract=2,pages=[dict(page=1,fingerprint='abc')],document_check=dict(revision=4,final=True,passed=True,collision_check_executed=True),aesthetic_reviews={},visual_request=dict(eligible=True,revision=4,fingerprints=['abc'],request_id='request'))
    assert delivery(state)['status']=='draft_pending_visual'
    state['aesthetic_reviews']={'1':dict(revision=4,page=1,fingerprint='abc',request_id='request',status='passed',issues=[])}
    assert delivery(state)['document_visual']=='pending'
    state['document_review']=dict(revision=4,fingerprints=['abc'],request_id='request',status='unavailable')
    assert delivery(state)['status']=='draft_visual_unavailable'
    state['document_review'].update(status='passed')
    assert delivery(state)['status']=='accepted'
    state['revision']=5
    assert delivery(state)['status']=='draft_pending_check'


def test_page_and_document_reviews_execute_separately_and_reject_stale_results(tmp_path):
    store=make_store(tmp_path,[section('body',['h','p'])])
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='科研报告'),dict(type='append_paragraph',block_id='p',text='研究方法和实验结果在正文中清晰呈现。')]))
    checked=store.check_document(final=True)
    assert checked['passed'],checked['repair_targets']
    adapter=load_adapter();calls=[]
    def model(system,text,images,schema):
        calls.append(dict(system=system,images=len(images),schema=schema.__name__))
        assert images[0][1].startswith(b'\x89PNG')
        return dict(status='passed',summary='Inspected the actual supplied image',issues=[])
    service=adapter.Documents(store.path.parent,host=dict(private_root=tmp_path/'private',vision=lambda:('fixture-vision',model)))
    service.reviews.resume(store.path)
    deadline=time.monotonic()+20
    while time.monotonic()<deadline:
        state=store.metadata()
        if state.get('document_review'):break
        service.sync();time.sleep(.05)
    else:pytest.fail('Independent whole-document review did not finish')
    assert {call['schema'] for call in calls}=={'PageReview','DocumentReview'}
    assert len(state['aesthetic_reviews'])==len(checked['pages'])
    assert state['document_review']['reviewed_pages']==len(checked['pages'])
    assert service.quality_delivery(state)['visual_complete']
    old=state['document_review']
    store.apply_one(envelope(store,'edit',operation=dict(type='replace_text',block_id='p',old='清晰',new='完整清晰')))
    assert not service.reviews.record(store,'report',old['revision'],None,old['fingerprints'],old)
    assert store.metadata()['document_review'] is None
    service.close()


def load_adapter():
    spec=importlib.util.spec_from_file_location('cn_quality_adapter',ROOT/'docx-ooxml-skill/platform_adapter.py');module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module);return module


def test_actual_cross_page_table_without_header_is_repaired(tmp_path):
    store=make_store(tmp_path,[section('body',['h','table'],tables=['table'])])
    ops=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 长表格验证'),dict(type='append_table',block_id='table',rows=[['Identifier','Procedure','Evidence']]+[[f'Case-{i:03d}',f'Validate reproducible data for test observation {i:03d} across physical pages.',f'Recorded outcome {i:03d}'] for i in range(1,60)],keep_together=False)]
    store.apply_section(envelope(store,'table',section_id='body',operations=ops))
    # A corrupted imported table fixture: preserve its text and remove pagination
    # protection, then let the production check/repair path handle the revision.
    parts=a.o.read_parts(store.path);root=a.o.parse_xml(parts[a.o.MAIN])
    for control in root.xpath('//w:tbl//w:trPr/w:tblHeader|//w:tbl//w:trPr/w:cantSplit',namespaces=a.o.NS):control.getparent().remove(control)
    parts[a.o.MAIN]=a.o.xml_bytes(root)
    with store.locked() as(c,state):store.commit(c,state,a.packed(parts),'import-bad-table',dict(fixture='missing-header'),['table'])
    check=store.check_document(final=True,auto_repair=False)
    assert len(check['pages'])>1
    assert any(t['code'] in ('table_header_missing','long_table_pagination') and t['block_id']=='table' for t in check['repair_targets'])
    repair=store.repair_document(check['revision'],'repair-table')
    assert repair['recheck']['passed'],repair['remaining']
    assert not any(t['code']=='table_header_missing' for t in repair['remaining'])


def test_no_vision_model_produces_page_and_document_unavailable(tmp_path):
    store=make_store(tmp_path,[section('body',['p'])]);store.apply_section(envelope(store,'p',section_id='body',operations=[dict(type='append_paragraph',block_id='p',text='科研报告的视觉验收不可伪造通过。')]))
    check=store.check_document(final=True);assert check['passed']
    adapter=load_adapter();service=adapter.Documents(store.path.parent,host=dict(private_root=tmp_path/'private'))
    service.reviews.resume(store.path);deadline=time.monotonic()+15
    while not store.metadata().get('document_review') and time.monotonic()<deadline:service.sync();time.sleep(.05)
    state=store.metadata();assert state['document_review']['status']=='unavailable'
    assert all(r['status']=='unavailable' for r in state['aesthetic_reviews'].values())
    result=store.finalize(state['revision']);assert result['publication_status']=='draft'
    assert result['page_visual']==result['document_visual']=='unavailable'
    assert not state['finalized'];service.close()


def test_reflow_invalidates_every_old_page_and_document_review(tmp_path):
    store=make_store(tmp_path,[section('body',['h']+[f'p{i}' for i in range(8)])]);store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 Reflow')]+[dict(type='append_paragraph',block_id=f'p{j}',text=' '.join(f'Observation {j:02d}.{i:03d} records the reproducible input and expected outcome.' for i in range(30))) for j in range(8)]))
    checked=store.check_document(final=True);assert checked['passed']
    old=store.metadata();assert len(old['pages'])>=2
    request_id=old['visual_request']['request_id']
    with store.locked() as(c,state):
        state['aesthetic_reviews']={str(p['page']):dict(revision=state['revision'],page=p['page'],fingerprint=p['fingerprint'],request_id=request_id,status='passed',issues=[]) for p in state['pages']}
        state['document_review']=dict(revision=state['revision'],fingerprints=[p['fingerprint'] for p in state['pages']],request_id=request_id,status='passed',issues=[])
        store.save_state(c,state);c.commit()
    store.apply_one(envelope(store,'reflow',operation=dict(type='set_paragraph_format',block_id='h',space_after_twips=5000)))
    checked=store.check_document(final=True);state=store.metadata()
    assert state['aesthetic_reviews']=={} and state['document_review'] is None
    assert any(p['fingerprint']!=old['pages'][i]['fingerprint'] for i,p in enumerate(checked['pages']) if i<len(old['pages']))
    assert a._sibling('quality_status').delivery(state)['page_visual']=='pending'


def test_interrupted_repair_replays_committed_step_and_preserves_revision(tmp_path,monkeypatch):
    store=make_store(tmp_path,[section('cover',['title','date'],'cover')]);store.apply_section(envelope(store,'cover',section_id='cover',operations=[dict(type='append_paragraph',block_id='title',style='CoverTitle',text='科研项目总结'),dict(type='set_paragraph_format',block_id='title',space_after_twips=14000),dict(type='append_paragraph',block_id='date',style='CoverDate',text='2026 年 11 月')]))
    check=store.check_document(final=True,auto_repair=False);real=store.commit
    def crash(*args,**kwargs):
        result=real(*args,**kwargs)
        if result.get('operation_id')=='recover-repair':raise RuntimeError('crash after repair commit')
        return result
    monkeypatch.setattr(store,'commit',crash)
    with pytest.raises(RuntimeError,match='crash after repair commit'):store.repair_document(check['revision'],'recover-repair')
    revision=store.metadata()['revision'];assert revision==check['revision']+1
    monkeypatch.setattr(store,'commit',real)
    result=store.repair_document(check['revision'],'recover-repair')
    assert result['recheck']['passed'] and result['revision']==revision and result['repair_attempts']==1


def test_journal_accepts_one_and_two_column_designs(tmp_path):
    for columns in (1,2):
        store=a.DocumentStore(tmp_path/f'journal-{columns}.docx');store.init('journal',design='cn-journal-paper',columns=columns)
        root=a.o.parse_xml(a.o.read_parts(store.path)[a.o.MAIN])
        assert root.xpath('string(//w:sectPr/w:cols/@w:num)',namespaces=a.o.NS)==str(columns)


def test_actual_libreoffice_textbox_image_collision_and_square_wrap(tmp_path):
    from PIL import Image
    Image.new('RGB',(160,110),'#4477aa').save(tmp_path/'image.png')
    parts=a.o.default_package()
    parts,_,_=a.mutate(parts,dict(type='insert_image',block_id='image',path='image.png',width_cm=4,float='left'),tmp_path)
    root=a.o.parse_xml(parts[a.o.MAIN]);wp='http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing'
    anchor=root.find('.//{%s}anchor'%wp)
    for tag,value in [('positionH',75),('positionV',100)]:
        node=anchor.find('{%s}%s'%(wp,tag));node.set('relativeFrom','page')
        for child in list(node):node.remove(child)
        a.o.etree.SubElement(node,'{%s}posOffset'%wp).text=str(value*12700)
    old=anchor.find('{%s}wrapSquare'%wp);old.getparent().replace(old,a.o.etree.Element('{%s}wrapNone'%wp))
    textbox=a.o.etree.fromstring(('''<w:p xmlns:w="'''+a.o.W+'''" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:b="'''+a.BLOCK_NS+'''" b:id="textbox-anchor"><w:r><w:pict><v:shape id="textbox" style="position:absolute;margin-left:80pt;margin-top:110pt;width:180pt;height:40pt;mso-position-horizontal-relative:page;mso-position-vertical-relative:page" stroked="f" filled="f"><v:textbox inset="0,0,0,0"><w:txbxContent><w:p b:id="textbox-text"><w:r><w:t>Independent collision textbox</w:t></w:r></w:p></w:txbxContent></v:textbox></v:shape></w:pict></w:r></w:p>''').encode())
    body=root.find(a.o.q(a.o.W,'body'));body.insert(0,textbox);parts[a.o.MAIN]=a.o.xml_bytes(root)
    template=tmp_path/'collision-template.docx';template.write_bytes(a.packed(parts))
    store=a.DocumentStore(tmp_path/'collision.docx');store.init('collision',template=template,quality_contract=2)
    result=store.check_document(final=True,auto_repair=False)
    targets=[t for t in result['repair_targets'] if t['code']=='text_image_collision']
    assert targets and any(t['block_id']=='textbox-text' for t in targets),result['repair_targets']
    assert all(t['detail']['image_bbox'] and t['detail']['text_bbox'] for t in targets)
    # Normal square wrapping is rendered by Word itself and must remain accepted.
    parts=a.o.default_package();parts,_,_=a.mutate(parts,dict(type='insert_image',block_id='image',path='image.png',width_cm=4,float='left'),tmp_path)
    parts,_,_=a.mutate(parts,dict(type='append_paragraph',block_id='text',text='A normal paragraph flows around the image without occupying the same visual space. '*10),tmp_path)
    template=tmp_path/'wrap-template.docx';template.write_bytes(a.packed(parts));normal=a.DocumentStore(tmp_path/'wrapped.docx');normal.init('wrapped',template=template,quality_contract=2)
    result=normal.check_document(final=True,auto_repair=False)
    assert not any(t['code'] in ('text_image_collision','text_collision') for t in result['repair_targets']),result['repair_targets']


def test_render_failure_and_unknown_visual_verdicts_never_pass():
    delivery=a._sibling('quality_status').delivery
    state=dict(revision=2,quality_contract=2,pages=[],document_check=dict(revision=2,final=True,passed=False,collision_check_executed=False,render_error='Render failed'))
    assert delivery(state)['deterministic']=='failed'
    state.update(pages=[dict(page=1,fingerprint='fp')],visual_request=dict(eligible=True,revision=2,fingerprints=['fp'],request_id='q'),aesthetic_reviews={'1':dict(revision=2,fingerprint='fp',request_id='q',status='unexpected')})
    assert delivery(state)['page_visual']=='pending'


def test_unused_template_style_font_does_not_block_chinese_layout(tmp_path):
    store=make_store(tmp_path,[section('body',['p'])]);store.apply_section(envelope(store,'p',section_id='body',operations=[dict(type='append_paragraph',block_id='p',text='正文使用实际安装的中文字体，不受未使用的模板样式影响。')]))
    parts=a.o.read_parts(store.path);styles=a.o.parse_xml(parts['word/styles.xml']);style=a.o.etree.SubElement(styles,a.o.q(a.o.W,'style'),{a.o.q(a.o.W,'styleId'):'Unused',a.o.q(a.o.W,'type'):'paragraph'});pr=a.o.etree.SubElement(style,a.o.q(a.o.W,'rPr'));a.o.etree.SubElement(pr,a.o.q(a.o.W,'rFonts'),{a.o.q(a.o.W,'eastAsia'):'Missing Unused Font'})
    parts['word/styles.xml']=a.o.xml_bytes(styles)
    with store.locked() as(c,state):store.commit(c,state,a.packed(parts),'unused-style',dict(fixture='unused-font'),[])
    result=store.check_document(final=True,auto_repair=False)
    assert result['passed'],result['repair_targets']


@pytest.mark.parametrize('identity',['cn-thesis-general','cn-engineering-thesis','cn-journal-paper','cn-research-report'])
def test_all_cn_designs_pass_real_final_document_check(tmp_path,identity):
    store=make_store(tmp_path,[section('body',['h','p'])],design=identity)
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 科研方法'),dict(type='append_paragraph',block_id='p',text='本节按选定设计组织研究方法、数据记录及验证过程。中文与 Latin text 分别使用指定字体。')]))
    result=store.check_document(final=True)
    assert result['passed'] and result['collision_check_executed'],result['repair_targets']


def test_two_column_journal_sizes_default_components_to_column(tmp_path):
    store=make_store(tmp_path,[section('body',['h','p','eq','chart','table'],equations=['eq'],figures=['chart'],tables=['table'])],design='cn-journal-paper')
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 双栏研究'),dict(type='append_paragraph',block_id='p',text='期刊图表与公式应适应实际栏宽。'),dict(type='insert_equation',block_id='eq',latex=r'E=mc^2',numbered=True),dict(type='insert_chart',block_id='chart',chart=dict(type='column',categories=['A','B'],series=[dict(name='Result',values=[1,2])])),dict(type='append_table',block_id='table',rows=[['Identifier','Observation'],['Run A','Result A'],['Run B','Result B']])]))
    root=a.o.parse_xml(a.o.read_parts(store.path)[a.o.MAIN]);width=a._sibling('academic_blocks')._text_width(root,a.o)
    assert 3000<width<4500
    assert int(root.xpath('string(//*[local-name()="extent"]/@cx)'))<=width*635+10000
    assert root.xpath('//*[@b:id="eq"]/w:pPr/w:pStyle[@w:val="Equation"]',namespaces=dict(a.o.NS,b=a.BLOCK_NS))
    result=store.check_document(final=True);assert result['passed'],result['repair_targets']


def test_background_inflight_result_does_not_pollute_new_revision(tmp_path):
    store=make_store(tmp_path,[section('body',['p'])]);store.apply_section(envelope(store,'p',section_id='body',operations=[dict(type='append_paragraph',block_id='p',text='后台审查期间允许正文继续更新。')]))
    assert store.check_document(final=True)['passed']
    started=threading.Event();release=threading.Event()
    def model(system,text,images,schema):
        started.set();release.wait(10);return dict(status='passed',summary='Reviewed the supplied old snapshot',issues=[])
    service=load_adapter().Documents(store.path.parent,host=dict(private_root=tmp_path/'private',vision=lambda:('slow-test',model)))
    try:
        service.reviews.resume(store.path);assert started.wait(10)
        store.apply_one(envelope(store,'edit',operation=dict(type='replace_text',block_id='p',old='继续',new='局部继续')))
        release.set();deadline=time.monotonic()+15
        while service.reviews.inflight and time.monotonic()<deadline:time.sleep(.05)
        state=store.metadata();assert state['aesthetic_reviews']=={} and state['document_review'] is None
        assert not state['finalized']
    finally:release.set();service.close()


def test_repeated_final_check_cannot_restart_stopped_automatic_repairs(tmp_path,monkeypatch):
    store=a.DocumentStore(tmp_path/'bounded.docx');store.init('bounded',design='cn-thesis-general')
    revision=store.metadata()['revision'];failed=dict(passed=False,revision=revision,repair_targets=[dict(code='cover_overflow',block_id='cover')]);calls=[]
    monkeypatch.setattr(store,'_workflow',lambda *args,**kwargs:dict(failed))
    def repair(*args,**kwargs):
        calls.append(args);return dict(revision=revision,recheck=failed,repair_attempts=3,remaining=failed['repair_targets'],exhausted=True,stop_reason='repeated_errors')
    monkeypatch.setattr(store,'repair_document',repair)
    assert store.check_document(final=True)['repair_summary']['exhausted']
    assert store.check_document(final=True)['repair_summary']['exhausted']
    assert len(calls)==1


def test_progressing_repairs_render_and_recheck_more_than_three_revisions(tmp_path,monkeypatch):
    from types import SimpleNamespace
    blocks=[b for i in range(5) for b in (f'h{i}',f'p{i}')]
    store=make_store(tmp_path,[section('body',blocks)])
    operations=[]
    for i in range(5):operations.extend([dict(type='append_paragraph',block_id=f'h{i}',style='Heading1',text=f'{i+1} 研究章节'),dict(type='set_paragraph_format',block_id=f'h{i}',keep_next=False),dict(type='append_paragraph',block_id=f'p{i}',text=f'第 {i+1} 节记录独立的研究方法与观测结果。')])
    store.apply_section(envelope(store,'body',section_id='body',operations=operations))
    before={b['block_id']:b['text'] for b in store.status()['blocks']}
    workflow=a._sibling('document_workflow');inspect=workflow.inspect_parts
    # Model a checker that exposes the next dependent structural defect only
    # after the preceding one is fixed. The mutations and renders remain real.
    def next_finding(parts,api):
        findings=inspect(parts,api)
        return findings[:1]
    monkeypatch.setattr(workflow,'inspect_parts',next_finding)
    api=SimpleNamespace(o=a.o,identifier=a.identifier,BLOCK_ID=a.BLOCK_ID,BLOCK_NS=a.BLOCK_NS,packed=a.packed,mutate=a.mutate,_sibling=a._sibling,repair_policy=a.repair_policy())
    check=workflow.check_document(store,True,api)
    result=workflow.repair_document(store,check['revision'],'progressive-repair',api)
    assert result['repair_attempts']==5 and result['recheck']['passed']
    assert result['stop_reason'] is None
    state=store.metadata();assert state['render_revision']==result['revision']
    for attempt in state['repair_runs']['progressive-repair']['attempts']:
        assert (store.render_directory(attempt['revision'])/'preview.pdf').is_file()
    assert before=={b['block_id']:b['text'] for b in store.status()['blocks']}


def test_review_regions_only_expose_exact_unique_pdf_block_matches(tmp_path):
    store=make_store(tmp_path,[section('body',['p1','p2','unique'])])
    store.apply_section(envelope(store,'regions',section_id='body',operations=[dict(type='append_paragraph',block_id='p1',text='重复出现的段落内容不得猜测所属 Block。'),dict(type='append_paragraph',block_id='p2',text='重复出现的段落内容不得猜测所属 Block。'),dict(type='append_paragraph',block_id='unique',text='这段独立说明只出现一次，允许使用实际渲染坐标定位。')]))
    result=store.check_document(final=True)
    regions=result['geometry']['block_regions']
    assert 'p1' not in regions and 'p2' not in regions
    assert regions['unique'][0]['source']=='pdf_text_exact'
    x,y,w,h=regions['unique'][0]['bbox']
    assert 0<=x<x+w<=1 and 0<=y<y+h<=1
    assert regions['unique'][0]['page']==1
