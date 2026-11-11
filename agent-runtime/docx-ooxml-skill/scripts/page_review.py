"""Conservative layout checks over an actual LibreOffice PDF, never visual QA.

Heuristics can detect geometry and text placement, not visual correctness.
Every new page therefore retains visual_review=pending until actual inspection.
"""
import hashlib
import json
import re
import shutil
import subprocess


def normalized(text):
    return re.sub(r'\s+', '', text)


def analyze_pages(parts, pdf, engine, final=False):
    o = engine
    root = o.parse_xml(parts[o.MAIN])
    ns = o.NS
    sections = root.findall('.//' + o.q(o.W, 'sectPr'))
    margin_abnormal = False
    for section in sections:
        size = section.find(o.q(o.W, 'pgSz'))
        margins = section.find(o.q(o.W, 'pgMar'))
        if size is None or margins is None:
            margin_abnormal = True
            continue
        width, height = (int(size.get(o.q(o.W, k), 0)) for k in ('w', 'h'))
        left, right, top, bottom = (int(margins.get(o.q(o.W, k), 0)) for k in ('left', 'right', 'top', 'bottom'))
        if min(left, right, top, bottom) < 180 or left + right >= width or top + bottom >= height:
            margin_abnormal = True
    texts = [normalized(p.get_text()) for p in pdf]
    headings = [o.ptext(p) for p in root.iter(o.q(o.W, 'p'))
        if p.xpath('./w:pPr/w:pStyle[starts-with(@w:val,"Heading") or starts-with(@w:val,"heading")]', namespaces=ns)]
    document_text = normalized(o.ptext(root))
    split_pages = set()
    uncertain_tables = 0
    for table in root.iter(o.q(o.W, 'tbl')):
        # A bounded table spanning pages needs a deliberate repair or review.
        samples = [normalized(o.ptext(p)) for p in table.iter(o.q(o.W, 'p')) if len(normalized(o.ptext(p))) >= 3 and document_text.count(normalized(o.ptext(p))) == 1]
        if not samples:
            uncertain_tables += 1
        hits = {i for i, text in enumerate(texts) if any(sample in text for sample in samples)}
        if len(hits) > 1:
            rows = list(table.iter(o.q(o.W, 'tr')))
            header = rows[0].find('./'+o.q(o.W,'trPr')+'/'+o.q(o.W,'tblHeader')) if rows else None
            protected = all(tr.find('./'+o.q(o.W,'trPr')+'/'+o.q(o.W,'cantSplit')) is not None for tr in rows)
            # Flowing tables with repeating headers and unsplit rows are expected.
            keep_chain = bool(table.xpath('.//w:pPr/w:keepNext[not(@w:val="0" or @w:val="false" or @w:val="off")]', namespaces=ns))
            if header is None or not protected or keep_chain:
                split_pages.update(hits)
    fonts_missing = []
    full_text = ''.join(texts)
    if re.search(r'[\u3400-\u9fff]', full_text):
        declared = set()
        styles=o.parse_xml(parts['word/styles.xml'])
        index={s.get(o.q(o.W,'styleId')):s for s in styles}
        default=styles.xpath('string(./w:docDefaults/w:rPrDefault/w:rPr/w:rFonts/@w:eastAsia)',namespaces=ns)
        def inherited_font(style):
            seen=set()
            while style in index and style not in seen:
                seen.add(style);node=index[style]
                value=node.xpath('string(./w:rPr/w:rFonts/@w:eastAsia)',namespaces=ns)
                if value:return value
                style=node.xpath('string(./w:basedOn/@w:val)',namespaces=ns)
            return default
        for name,data in parts.items():
            if name!=o.MAIN and not (name.startswith(('word/header','word/footer')) and name.endswith('.xml')):continue
            for paragraph in o.parse_xml(data).iter(o.q(o.W,'p')):
                style=paragraph.xpath('string(./w:pPr/w:pStyle/@w:val)',namespaces=ns) or 'Normal'
                for run in paragraph.iter(o.q(o.W,'r')):
                    if not re.search(r'[\u3400-\u9fff]',o.ptext(run)):continue
                    font=run.xpath('string(./w:rPr/w:rFonts/@w:eastAsia)',namespaces=ns) or inherited_font(style)
                    if font:declared.add(font)
        for font in sorted(declared):
            if not shutil.which('fc-match'):
                fonts_missing.append('fontconfig unavailable: ' + font)
                continue
            matched = subprocess.run(['fc-match', '-f', '%{family}', font], capture_output=True, text=True, timeout=5).stdout
            if font.casefold() not in [f.strip() for f in matched.casefold().split(',')]:
                fonts_missing.append(font)
    block_samples = [(node.get('{urn:deep-agent:docx:blocks:v1}id'), normalized(o.ptext(node)))
        for node in root.iter() if node.get('{urn:deep-agent:docx:blocks:v1}id')]
    page_blocks = [[] for _ in texts]
    for block_id, sample in block_samples:
        if len(sample) < 3: continue
        hits = [i for i, text in enumerate(texts) if sample in text]
        if len(hits) == 1: page_blocks[hits[0]].append(block_id)
    paragraph_samples = [(p.get('{urn:deep-agent:docx:blocks:v1}id'), normalized(o.ptext(p))) for p in root.iter(o.q(o.W,'p')) if not p.xpath('ancestor::w:tbl',namespaces=ns) and len(normalized(o.ptext(p))) > 20]
    page_lines = [[normalized(line) for line in page.get_text().splitlines() if normalized(line)] for page in pdf]
    lonely_lines = set()
    lonely_blocks = {}
    for i in range(len(page_lines)-1):
        left, right = page_lines[i], page_lines[i+1]
        if not left or not right: continue
        for block_id, sample in paragraph_samples:
            if len(left[-1]) >= 8 and len(right[0]) >= 8 and left[-1]+right[0] in sample:
                for page_index, lines in ((i,left),(i+1,right)):
                    if sum(line in sample for line in lines)==1:
                        lonely_lines.add(page_index)
                        if block_id: lonely_blocks.setdefault(page_index,[]).append(block_id)
    pages = []
    for i, page in enumerate(pdf):
        rect = page.rect
        overflow = False
        for block in page.get_text('blocks'):
            x0, y0, x1, y1 = block[:4]
            if x0 < -1 or y0 < -1 or x1 > rect.width + 1 or y1 > rect.height + 1:
                overflow = True
        for image in page.get_image_info():
            x0, y0, x1, y1 = image['bbox']
            if x0 < -1 or y0 < -1 or x1 > rect.width + 1 or y1 > rect.height + 1:
                overflow = True
        lines = [normalized(line) for line in page.get_text().splitlines() if normalized(line)]
        complete = final or i < len(pdf) - 1
        orphan = complete and bool(lines and any(normalized(h) and lines[-1].endswith(normalized(h)) for h in headings))
        blank = not lines and not page.get_image_info() and not page.get_drawings()
        # Require a uniquely recognizable paragraph continuation across pages.
        # A one-line cover, formula or diagram page is not evidence of a widow.
        widow_orphan = complete and i in lonely_lines
        block_ids = page_blocks[i]
        checks = dict(blank_page=blank, widow_orphan=widow_orphan, ooxml_valid=True, render_success=True, content_overflow=overflow,
            table_split=i in split_pages, heading_orphan=orphan, margins_abnormal=margin_abnormal,
            fonts_missing=fonts_missing, visual_review='pending', warnings=['Table text cannot be uniquely mapped; inspect actual table layout'] if uncertain_tables else [])
        checks['automatic_passed'] = not (overflow or i in split_pages or orphan or margin_abnormal or fonts_missing or blank or widow_orphan)
        # Render fingerprint invalidates previous visual reviews after any reflow,
        # including images, font substitution, headers, and page renumbering.
        fingerprint = hashlib.sha256(page.get_pixmap(alpha=False).samples).hexdigest()
        complete = final or i < len(pdf) - 1
        pages.append(dict(page=i + 1, block_ids=block_ids, widow_blocks=lonely_blocks.get(i, []), complete=complete, fingerprint=fingerprint, checks=checks,
            image='page-%03d.png' % (i + 1), status='failed' if not checks['automatic_passed'] else 'pending' if complete else 'writing'))
    return pages


def review_pages(docx, output, engine, final=False, render=True):
    import pymupdf as fitz
    if render:
        engine.run_render(docx, output)
    parts = engine.read_parts(docx)
    validation = engine.validate_parts(parts)
    if not validation['ok']:
        raise ValueError('Structural validation failed')
    with fitz.open(output / 'preview.pdf') as pdf:
        pages = analyze_pages(parts, pdf, engine, final)
    (output / 'checks.json').write_text(json.dumps(pages, ensure_ascii=False, indent=2))
    return pages
