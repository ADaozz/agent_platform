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


def make_store(tmp_path,sections,columns=None):
    store=a.DocumentStore(tmp_path/'report.docx');store.init('report',design='cn-thesis-general',columns=columns)
    plan=dict(version=1,document_id='report',title='科研报告',sections=sections)
    store.save_plan(envelope(store,'plan',plan=plan));return store


def section(identity,blocks,kind='body',**extra):
    return dict(id=identity,title=identity,requirements='检查组件与排版',block_ids=blocks,kind=kind,**extra)


def test_bundled_design_defines_separate_chinese_and_latin_fonts(tmp_path):
    assert [style['id'] for style in a._sibling('document_design').list_styles()] == ['cn-thesis-general']
    store=a.DocumentStore(tmp_path/'report.docx');store.init('report',design='cn-thesis-general')
    parts=a.o.read_parts(store.path);styles=a.o.parse_xml(parts['word/styles.xml'])
    normal=styles.xpath('//w:style[@w:styleId="Normal"]',namespaces=a.o.NS)[0]
    assert normal.xpath('string(./w:rPr/w:rFonts/@w:eastAsia)',namespaces=a.o.NS)=='SimSun'
    assert normal.xpath('string(./w:rPr/w:rFonts/@w:ascii)',namespaces=a.o.NS)=='Liberation Serif'
    assert normal.xpath('string(./w:rPr/w:sz/@w:val)', namespaces=a.o.NS) == '24'
    assert normal.xpath('string(./w:pPr/w:ind/@w:firstLineChars)', namespaces=a.o.NS) == '200'
    numbering = a.o.parse_xml(parts['word/numbering.xml'])
    assert numbering.xpath('//w:lvl/w:pStyle/@w:val', namespaces=a.o.NS) == ['Heading1', 'Heading2', 'Heading3']
    assert numbering.xpath('//w:lvl/w:lvlText/@w:val', namespaces=a.o.NS) == ['第%1章', '%1.%2', '%1.%2.%3']
    assert styles.xpath('//w:style/w:pPr/w:numPr/w:numId/@w:val', namespaces=a.o.NS) == ['1', '1', '1']
    config=store.metadata()['selected_design']
    assert config['sources'] and {'cover','abstract','toc','equation','citations','references','pagination'}<=config['components'].keys()
    assert store.metadata()['quality_contract']==2


def test_general_thesis_table_and_caption_defaults(tmp_path):
    from PIL import Image

    Image.new('RGB', (160, 80), '#abc4d6').save(tmp_path / 'figure.png')
    store = make_store(tmp_path, [section('body', ['title', 'table', 'note', 'figure', 'figure-title', 'complex-table'])])
    store.apply_one(envelope(store, 'title', operation=dict(
        type='insert_caption', block_id='title', label='表', text='样本统计')))
    store.apply_section(envelope(store, 'body', section_id='body', operations=[
        dict(type='append_table', block_id='table', rows=[['分组', '人数'], ['甲组', '24'], ['乙组', '12']]),
        dict(type='append_paragraph', block_id='note', style='TableNote', text='注：示例数据。'),
        dict(type='insert_image', block_id='figure', path='figure.png', width_cm=4),
        dict(type='insert_caption', block_id='figure-title', label='图', text='样本分布'),
        dict(type='insert_table', block_id='complex-table', columns=[{}, {}], header_rows=2,
             rows=[[dict(text='分组信息', colspan=2)], ['分组', '人数'], ['甲组', '24']]),
    ]), asset_root=tmp_path)

    parts = a.o.read_parts(store.path)
    styles = a.o.parse_xml(parts['word/styles.xml'])
    root = a.o.parse_xml(parts[a.o.MAIN])
    ns = {**a.o.NS, 'b': a.BLOCK_NS}
    blocks = root.xpath('/w:document/w:body/*[@b:id]', namespaces=ns)
    assert [node.get(a.BLOCK_ID) for node in blocks] == ['title', 'table', 'note', 'figure', 'figure-title', 'complex-table']
    for block, style_id in [(blocks[0], 'TableCaption'), (blocks[2], 'TableNote'), (blocks[4], 'Caption')]:
        assert block.xpath('string(w:pPr/w:pStyle/@w:val)', namespaces=ns) == style_id
        if style_id == 'TableNote':
            continue
        style = styles.xpath('w:style[@w:styleId=$id]', id=style_id, namespaces=ns)[0]
        assert style.xpath('string(w:pPr/w:jc/@w:val)', namespaces=ns) == 'center'
        assert style.xpath('string(w:rPr/w:sz/@w:val)', namespaces=ns) == '21'
        assert style.xpath('string(w:rPr/w:rFonts/@w:eastAsia)', namespaces=ns) == 'Noto Serif CJK SC'
    for table, last_header in [(blocks[1], 1), (blocks[5], 2)]:
        borders = table.xpath('w:tblPr/w:tblBorders/*[@w:val="single"]', namespaces=ns)
        assert [a.o.etree.QName(border).localname for border in borders] == ['top', 'bottom']
        ruled_rows = table.xpath('w:tr[w:tc/w:tcPr/w:tcBorders/w:bottom[@w:val="single"]]', namespaces=ns)
        assert ruled_rows == table.xpath('w:tr[$row]', row=last_header, namespaces=ns)
        assert not table.xpath('w:tr/w:tc/w:tcPr/w:tcBorders/w:top', namespaces=ns)


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
    store = make_store(tmp_path, [
        section('abstract', ['abstract'], 'abstract'),
        section('toc', ['toc'], 'toc'),
        section('body', ['h', 'h2', 'h3', 'p']),
        section('references', ['references', 'reference'], 'references'),
        section('appendix', ['appendix', 'appendix-text'], 'appendix'),
    ])
    store.apply_section(envelope(store, 'abstract', section_id='abstract', operations=[
        dict(type='append_paragraph', block_id='abstract', text='摘要介绍本研究的主要问题。'),
    ]))
    store.apply_section(envelope(store, 'toc', section_id='toc', operations=[
        dict(type='insert_toc', block_id='toc', levels=3),
    ]))
    store.apply_section(envelope(store, 'body', section_id='body', operations=[
        dict(type='append_paragraph', block_id='h', style='Heading1', text='研究方法'),
        dict(type='append_paragraph', block_id='h2', style='Heading2', text='实验步骤'),
        dict(type='append_paragraph', block_id='h3', style='Heading3', text='样本选择'),
        dict(type='append_paragraph', block_id='p', text='正文介绍研究对象、可追踪的实验方法与检查结果。'),
    ]))
    store.apply_section(envelope(store, 'references', section_id='references', operations=[
        dict(type='append_paragraph', block_id='references', style='Heading1', text='参考文献'),
        dict(type='append_paragraph', block_id='reference', style='Reference', text='示例参考文献条目。'),
    ]))
    store.apply_section(envelope(store, 'appendix', section_id='appendix', operations=[
        dict(type='append_paragraph', block_id='appendix', style='Heading1', text='附录材料'),
        dict(type='append_paragraph', block_id='appendix-text', text='附录列出研究补充材料。'),
    ]))
    check=store.check_document(final=True,auto_repair=False)
    assert any(t['code']=='toc_page_results' for t in check['repair_targets'])
    result=store.repair_document(check['revision'],'toc-repair')
    assert result['recheck']['passed'],result['recheck']['repair_targets']
    assert len(result['recheck']['pages']) == 5
    parts = a.o.read_parts(store.path)
    root = a.o.parse_xml(parts[a.o.MAIN])
    ns = a.o.NS
    assert root.xpath('//w:fldSimple[contains(@w:instr,"PAGEREF")]//w:t/text()', namespaces=ns) == ['1', '1', '1', '2', '3']
    assert root.xpath('//w:sdt//w:hyperlink/w:r/w:t/text()', namespaces=ns) == [
        '第1章 研究方法', '1.1 实验步骤', '1.1.1 样本选择', '参考文献', '附录材料']
    import pymupdf
    with pymupdf.open(store.render_directory(result['recheck']['revision']) / 'preview.pdf') as pdf:
        body = pdf[2]
        for label in ('第1章研究方法', '1.1实验步骤', '1.1.1样本选择'):
            assert label in ''.join(body.get_text().split())
        first_line = body.search_for('正文介绍研究对象')[0]
        assert first_line.x0 == pytest.approx(72 + 24, abs=0.6)
    assert len(root.xpath('//w:sdt//w:tab[@w:val="right" and @w:leader="dot"]', namespaces=ns)) == 5
    styles = a.o.parse_xml(parts['word/styles.xml'])
    heading = styles.xpath('w:style[@w:styleId="TOCHeading"]', namespaces=ns)[0]
    assert heading.xpath('string(w:pPr/w:jc/@w:val)', namespaces=ns) == 'center'
    assert heading.xpath('string(w:rPr/w:sz/@w:val)', namespaces=ns) == '32'
    assert heading.xpath('string(w:rPr/w:rFonts/@w:eastAsia)', namespaces=ns) == 'Noto Sans CJK SC'
    for level, size, indent in [(1, '24', ''), (2, '24', '240'), (3, '21', '420')]:
        style = styles.xpath('w:style[@w:styleId=$id]', id=f'TOC{level}', namespaces=ns)[0]
        assert style.xpath('string(w:pPr/w:ind/@w:left)', namespaces=ns) == indent
        assert style.xpath('string(w:pPr/w:spacing/@w:line)', namespaces=ns) == '300'
        assert style.xpath('string(w:rPr/w:sz/@w:val)', namespaces=ns) == size


@pytest.mark.skipif(not shutil.which('libreoffice'), reason='LibreOffice required')
def test_toc_continuation_pages_are_separate_from_body(tmp_path):
    import pymupdf

    body = [section(f'body-{i}', [f'{kind}-{n}' for n in range(i * 25, (i + 1) * 25)
                                  for kind in ('heading', 'text')]) for i in range(2)]
    store = make_store(tmp_path, [section('toc', ['toc'], 'toc'), *body])
    store.apply_section(envelope(store, 'toc', section_id='toc', operations=[
        dict(type='insert_toc', block_id='toc', levels=2),
    ]))
    for i, part in enumerate(body):
        operations = []
        for n in range(i * 25, (i + 1) * 25):
            operations.extend([
                dict(type='append_paragraph', block_id=f'heading-{n}', style='Heading1' if n in (0, 25) else 'Heading2',
                     text=f'{n + 1:02d} 目录条目测试'),
                dict(type='append_paragraph', block_id=f'text-{n}', text=f'正文专用内容标记 {n + 1:02d}'),
            ])
        store.apply_section(envelope(store, part['id'], section_id=part['id'], operations=operations))

    render = store.render_directory(store.metadata()['revision'])
    with pymupdf.open(render / 'preview.pdf') as pdf:
        pages = [page.get_text() for page in pdf]
    first_body = next(i for i, text in enumerate(pages) if '正文专用内容标记 01' in text)
    assert first_body >= 2
    assert '目录\n' in pages[0]
    assert all('正文专用内容标记' not in text and '目录条目测试' in text for text in pages[:first_body])
    assert '第1章' in pages[first_body]
    assert pages[first_body].index('01 目录条目测试') < pages[first_body].index('正文专用内容标记 01')


@pytest.mark.skipif(not shutil.which('libreoffice'), reason='LibreOffice required')
def test_thesis_page_numbers_continue_and_use_next_page_breaks(tmp_path):
    import pymupdf

    content = [
        ('cover', '封面', 'CoverTitle'),
        ('abstract', '中文摘要', 'AbstractTitle'),
        ('abstract', 'Abstract', 'AbstractTitle'),
        ('toc', '目录', 'TOCHeading'),
        ('body', '绪论', 'Heading1'),
        ('body', '研究方法', 'Heading1'),
        ('references', '参考文献', 'Normal'),
        ('appendix', '附录内容', 'Heading1'),
        ('acknowledgments', '致谢', 'Normal'),
    ]
    text_kinds = {'body', 'references', 'appendix', 'acknowledgments'}
    store = make_store(tmp_path, [section(f's-{i}', [f'p-{i}', f't-{i}'] if kind in text_kinds else [f'p-{i}'], kind)
                                  for i, (kind, _, _) in enumerate(content)])
    for i, (kind, title, style) in enumerate(content):
        op = (dict(type='insert_toc', block_id=f'p-{i}', levels=2) if kind == 'toc'
              else dict(type='append_paragraph', block_id=f'p-{i}', style=style, text=title))
        operations = [op]
        if kind in text_kinds:
            operations.append(dict(type='append_paragraph', block_id=f't-{i}', text=f'第 {i} 部分的页码排版测试内容。'))
        store.apply_section(envelope(store, f'op-{i}', section_id=f's-{i}', operations=operations))

    parts = a.o.read_parts(store.path)
    doc = a.o.parse_xml(parts[a.o.MAIN])
    ns = a.o.NS
    assert doc.xpath('//w:sectPr/w:type/@w:val', namespaces=ns) == ['nextPage', 'nextPage']
    assert doc.xpath('//w:sectPr/w:pgNumType/@w:fmt', namespaces=ns) == ['upperRoman', 'decimal']
    assert doc.xpath('//w:sectPr/w:pgNumType/@w:start', namespaces=ns) == ['1', '1']
    assert not doc.xpath('(//w:sectPr)[1]/w:footerReference', namespaces=ns)
    footer = a.o.parse_xml(parts['word/footer1.xml'])
    assert footer.xpath('normalize-space(//w:fldSimple/@w:instr)', namespaces=ns) == 'PAGE'
    assert footer.xpath('string(//w:jc/@w:val)', namespaces=ns) == 'center'
    style = a.o.parse_xml(parts['word/styles.xml']).xpath('w:style[@w:styleId="Footer"]', namespaces=ns)[0]
    assert style.xpath('string(w:rPr/w:rFonts/@w:ascii)', namespaces=ns) == 'Times New Roman'
    assert style.xpath('string(w:rPr/w:sz/@w:val)', namespaces=ns) == '21'

    render = store.render_directory(store.metadata()['revision'])
    with pymupdf.open(render / 'preview.pdf') as pdf:
        assert len(pdf) == len(content)
        for page, (kind, heading, _), label in zip(pdf, content, ['', 'I', 'II', 'III', '1', '2', '3', '4', '5']):
            assert heading in page.get_text()
            if kind == 'body':
                assert f'第{label}章{heading}' in ''.join(page.get_text().split())
            assert page.get_text(clip=(0, page.rect.height - 70, page.rect.width, page.rect.height)).strip() == label


def test_leader_dots_without_page_fields_cannot_pass(tmp_path):
    store=make_store(tmp_path,[section('toc',['toc-heading','fake'],'toc')])
    store.apply_section(envelope(store,'fake',section_id='toc',operations=[
        dict(type='append_paragraph',block_id='toc-heading',style='TOCHeading',text='目录'),
        dict(type='append_paragraph',block_id='fake',style='TOC1',text='研究方法 ............'),
    ]))
    result=store.check_document(final=True)
    assert not result['passed']
    assert [t['block_id'] for t in result['repair_targets'] if t['code']=='toc_page_numbers_missing'] == ['fake']
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


def test_margin_check_allows_hanging_punctuation_and_image_rounding(tmp_path):
    import pymupdf as fitz
    from PIL import Image

    parts = a.o.default_package()
    with fitz.open() as pdf:
        page = pdf.new_page()
        right = page.rect.width - 72
        for block_id, text, y, shift in [('hanging', '行末标点。', 150, 0), ('overflow', '正文越界。', 200, 6)]:
            parts, _, _ = a.mutate(parts, dict(type='append_paragraph', block_id=block_id, text=text), tmp_path)
            page.insert_text((right - 48 + shift, y), text, fontsize=12, fontname='china-s')
        figure = tmp_path / 'figure.png'
        Image.new('RGB', (20, 20), 'blue').save(figure)
        for x, y in [(80, 71.95), (120, 70), (160, -1)]:
            page.insert_image(fitz.Rect(x, y, x + 20, y + 20), filename=str(figure))
        findings = a._sibling('layout_review').inspect(parts, pdf, a.o, a.BLOCK_ID)['findings']
    assert [f['block_id'] for f in findings if f['code'] == 'content_outside_margins'] == ['overflow']
    assert [f['detail']['bbox'][0] for f in findings if f['code'] == 'image_outside_margins'] == [120]
    assert [f['detail']['bbox'][0] for f in findings if f['code'] == 'image_clipped'] == [160]


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


def agent_answers(store):
    review=a._sibling('agent_review')
    page=dict(status='passed',summary='逐页查看渲染图',checks={k:dict(verdict='ok',evidence='正文清晰，段距正常') for k in review.PAGE_CHECKS},issues=[])
    document=dict(status='passed',summary='查看整稿缩略图',checks={k:dict(verdict='ok',evidence='各页风格一致') for k in review.DOCUMENT_CHECKS},issues=[])
    return page,document


def test_agent_reviews_every_page_then_the_document_and_stale_results_are_rejected(tmp_path):
    store=make_store(tmp_path,[section('body',['h','p'])])
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='科研报告'),dict(type='append_paragraph',block_id='p',text='研究方法和实验结果在正文中清晰呈现。')]))
    checked=store.check_document(final=True)
    assert checked['passed'],checked['repair_targets']
    images=store.review_images()
    assert [p['page'] for p in images['pages']]==[p['page'] for p in checked['pages']]
    assert all(Path(p['image']).read_bytes().startswith(b'\x89PNG') for p in images['pages'])
    assert Path(images['document']['sheet']).read_bytes().startswith(b'\x89PNG') and not images['document']['reviewable']
    context=json.loads(Path(images['context_file']).read_text())
    assert context['request_id']==images['request_id'] and context['pages'][0]['blocks']
    page,document=agent_answers(store);revision=images['revision']
    with pytest.raises(ValueError,match='Review every page'):
        store.submit_review(dict(revision=revision,document=dict(review=document)))
    with pytest.raises(ValueError,match='request_id'):
        store.submit_review(dict(revision=revision,request_id='old',pages=[dict(page=1,review=page)]))
    with pytest.raises(ValueError,match='nothing recorded'):
        store.submit_review(dict(revision=revision,pages=[dict(page=1,review=dict(page,checks={}))]))
    flagged=dict(page,status='issues',issues=[dict(block_id='ghost',observation='页脚略靠下',suggestion='页脚上移',severity='minor')])
    result=store.submit_review(dict(revision=revision,request_id=images['request_id'],pages=[dict(page=p['page'],review=flagged if p['page']==1 else page) for p in images['pages']]))
    assert result['delivery']['page_visual']=='issues' and result['delivery']['document_visual']=='pending'
    state=store.metadata()
    assert state['aesthetic_reviews']['1']['issues'][0]['block_id'] is None and state['aesthetic_reviews']['1']['reviewer']=='main_agent'
    assert store.review_images()['document']['reviewable']
    store.submit_review(dict(revision=revision,pages=[dict(page=1,review=page)]))
    result=store.submit_review(dict(revision=revision,document=dict(review=document)))
    state=store.metadata()
    assert state['document_review']['reviewed_pages']==len(checked['pages']) and result['delivery']['status']=='accepted'
    assert store.finalize(revision)['publication_status']=='finalized'
    store.apply_one(envelope(store,'edit',operation=dict(type='replace_text',block_id='p',old='清晰',new='完整清晰')))
    assert store.metadata()['document_review'] is None and store.metadata()['aesthetic_reviews']=={}
    with pytest.raises(ValueError,match='Revision conflict'):
        store.submit_review(dict(revision=revision,pages=[dict(page=1,review=page)]))


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


def test_agent_that_cannot_view_images_leaves_an_unavailable_draft(tmp_path):
    store=make_store(tmp_path,[section('body',['p'])]);store.apply_section(envelope(store,'p',section_id='body',operations=[dict(type='append_paragraph',block_id='p',text='科研报告的视觉验收不可伪造通过。')]))
    check=store.check_document(final=True);assert check['passed']
    revision=store.metadata()['revision']
    store.submit_review(dict(revision=revision,pages=[dict(page=p['page'],unavailable='当前模型不支持图片输入') for p in check['pages']],document=dict(unavailable='当前模型不支持图片输入')))
    state=store.metadata();assert state['document_review']['status']=='unavailable'
    assert all(r['status']=='unavailable' and r['error']['code']=='agent_cannot_inspect' for r in state['aesthetic_reviews'].values())
    result=store.finalize(state['revision']);assert result['publication_status']=='draft'
    assert result['page_visual']==result['document_visual']=='unavailable'
    assert not store.metadata()['finalized']


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


def test_design_accepts_one_and_two_column_overrides(tmp_path):
    for columns in (1,2):
        store=a.DocumentStore(tmp_path/f'columns-{columns}.docx');store.init('report',design='cn-thesis-general',columns=columns)
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


def test_bundled_design_passes_real_final_document_check(tmp_path):
    store=make_store(tmp_path,[section('body',['h','p'])])
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 科研方法'),dict(type='append_paragraph',block_id='p',text='本节按选定设计组织研究方法、数据记录及验证过程。中文与 Latin text 分别使用指定字体。')]))
    result=store.check_document(final=True)
    assert result['passed'] and result['collision_check_executed'],result['repair_targets']


def test_two_column_design_sizes_default_components_to_column(tmp_path):
    store=make_store(tmp_path,[section('body',['h','p','eq','chart','table'],equations=['eq'],figures=['chart'],tables=['table'])],columns=2)
    store.apply_section(envelope(store,'body',section_id='body',operations=[dict(type='append_paragraph',block_id='h',style='Heading1',text='1 双栏研究'),dict(type='append_paragraph',block_id='p',text='期刊图表与公式应适应实际栏宽。'),dict(type='insert_equation',block_id='eq',latex=r'E=mc^2',numbered=True),dict(type='insert_chart',block_id='chart',chart=dict(type='column',categories=['A','B'],series=[dict(name='Result',values=[1,2])])),dict(type='append_table',block_id='table',rows=[['Identifier','Observation'],['Run A','Result A'],['Run B','Result B']])]))
    root=a.o.parse_xml(a.o.read_parts(store.path)[a.o.MAIN]);width=a._sibling('academic_blocks')._text_width(root,a.o)
    assert 3000<width<4500
    assert int(root.xpath('string(//*[local-name()="extent"]/@cx)'))<=width*635+10000
    assert root.xpath('//*[@b:id="eq"]/w:pPr/w:pStyle[@w:val="Equation"]',namespaces=dict(a.o.NS,b=a.BLOCK_NS))
    result=store.check_document(final=True);assert result['passed'],result['repair_targets']


def test_review_images_refuses_a_revision_without_a_final_check(tmp_path):
    store=make_store(tmp_path,[section('body',['p'])]);store.apply_section(envelope(store,'p',section_id='body',operations=[dict(type='append_paragraph',block_id='p',text='审查期间正文可以继续更新。')]))
    assert store.check_document(final=True)['passed'] and store.review_images()['pages']
    store.apply_one(envelope(store,'edit',operation=dict(type='replace_text',block_id='p',old='继续',new='局部继续')))
    with pytest.raises(ValueError,match='check-document --final'):store.review_images()
    state=store.metadata();assert state['aesthetic_reviews']=={} and state['document_review'] is None and not state['finalized']


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
