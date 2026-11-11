"""Final deterministic audit over OOXML semantics and the actual paginated PDF.

Bounding boxes are evidence, not independent objects: spans in the same paragraph,
math run, or table are not collisions. Header/footer fields and intentional tight
wrapping/cropping are handled separately. Uncertain source matches are never given
invented Block IDs and cannot be automatically rewritten.
"""
import hashlib
import io
import re
from collections import defaultdict


def norm(text):return re.sub(r'\s+','',text or '')


def inspect(parts,pdf,o,block_attribute,plan=None,design=None):
    root=o.parse_xml(parts[o.MAIN]);ns=o.NS
    paragraphs=[p for p in root.iter(o.q(o.W,'p')) if p.get(block_attribute)]
    nodes={n.get(block_attribute):n for n in root.iter() if n.get(block_attribute)}
    styles={n.get(o.q(o.W,'styleId')):n for n in o.parse_xml(parts['word/styles.xml'])}
    def font_size(p):
        style=p.xpath('string(./w:pPr/w:pStyle/@w:val)',namespaces=ns) or 'Normal';seen=set()
        while style in styles and style not in seen:
            seen.add(style);n=styles[style];size=n.xpath('string(./w:rPr/w:sz/@w:val)',namespaces=ns)
            if size:
                try:return float(size)/2
                except ValueError:break
            style=n.xpath('string(./w:basedOn/@w:val)',namespaces=ns)
        return 11
    records=[dict(id=p.get(block_attribute),node=p,text=norm(''.join(t.text or '' for t in p.iter(o.q(o.W,'t')) if next(t.iterancestors(o.q(o.W,'p')),None) is p)),size=font_size(p),table=next((t.get(block_attribute) for t in p.iterancestors(o.q(o.W,'tbl'))),None)) for p in paragraphs]
    records=[r for r in records if r['text']]
    by_id={r['id']:r for r in records};placements=defaultdict(set);page_spans=[];findings=[]
    def add(code,page=None,block=None,detail=None,operation=None,related=None):
        findings.append(dict(code=code,page=page,block_id=block,severity='error',deterministic=operation is not None,repairable=operation is not None,operation=operation,detail=detail,related_blocks=related or []))
    def source(text,size):
        text=norm(text)
        if len(text)<3:return None
        candidates=[r for r in records if text in r['text']]
        if not candidates:return None
        candidates.sort(key=lambda r:(abs(r['size']-size),len(r['text'])))
        if len(candidates)>1 and (abs(candidates[0]['size']-size),len(candidates[0]['text']))==(abs(candidates[1]['size']-size),len(candidates[1]['text'])):return None
        return candidates[0]
    # Record unique whole paragraph placements too, including empty visual borders.
    for index,page in enumerate(pdf):
        spans=[]
        for b in page.get_text('rawdict')['blocks']:
            for line in b.get('lines',[]):
                for s in line['spans']:
                    chars=s.get('chars',[]);s['text']=''.join(c['c'] for c in chars)
                    ink=[c['bbox'] for c in chars if c['c'].strip()]
                    if not ink:continue
                    # Justified trailing spaces have advance boxes outside margins,
                    # but no ink. Audit real non-space glyph bounds, not advances.
                    s['bbox']=(min(b[0] for b in ink),min(b[1] for b in ink),max(b[2] for b in ink),max(b[3] for b in ink))
                    s.pop('chars',None)
                    rec=source(s['text'],s['size']);item=dict(s,block_id=rec['id'] if rec else None,table=rec['table'] if rec else None)
                    spans.append(item)
                    if rec:placements[rec['id']].add(index+1)
        page_spans.append(spans)
        for rec in records:
            text=o.ptext(rec['node']).strip()
            if len(text)>=3 and page.search_for(text):placements[rec['id']].add(index+1)
    # Parent block placements include tables/content controls, but not entire body.
    for identity,node in nodes.items():
        for child in node.iter():
            if child is not node and child.get(block_attribute):placements[identity].update(placements.get(child.get(block_attribute),set()))
    # Each sectPr closes the preceding section, including a final body sectPr.
    body=root.find(o.q(o.W,'body'));sections=[];pending=[]
    for child in body:
        pending.extend([n.get(block_attribute) for n in child.iter() if n.get(block_attribute)])
        props=child if child.tag==o.q(o.W,'sectPr') else child.find('./'+o.q(o.W,'pPr')+'/'+o.q(o.W,'sectPr'))
        if props is not None:
            pages=set().union(*(placements.get(b,set()) for b in pending)) if pending else set()
            sections.append(dict(node=props,blocks=list(pending),pages=pages));pending=[]
    def section_for(page):
        return next((s for s in sections if page in s['pages']),sections[-1] if sections else None)
    def region(page):
        import pymupdf as fitz
        section=section_for(page.number+1)
        pr=section['node'] if section else None
        margin=pr.find(o.q(o.W,'pgMar')) if pr is not None else None
        if margin is None:return page.rect
        values={k:int(margin.get(o.q(o.W,k),'1440'))/20 for k in ('left','right','top','bottom')}
        return fitz.Rect(values['left'],values['top'],page.rect.width-values['right'],page.rect.height-values['bottom'])
    header_text=[];footer_text=[];has_page_field=False
    for name,data in parts.items():
        if name.startswith(('word/header','word/footer')) and name.endswith('.xml'):
            n=o.parse_xml(data);texts=[norm(o.ptext(p)) for p in n.iter(o.q(o.W,'p')) if norm(o.ptext(p))]
            (header_text if name.startswith('word/header') else footer_text).extend(texts)
            has_page_field=has_page_field or bool(n.xpath('//w:instrText[contains(text(),"PAGE")]|//w:fldSimple[contains(@w:instr,"PAGE")]',namespaces=ns))
    def furniture(span,page):
        text=norm(span['text']);area=region(page);box=span['bbox']
        outside=box[3]<=area.y0+2 or box[1]>=area.y1-2
        return outside and (any(text in t for t in header_text+footer_text) or (has_page_field and bool(re.fullmatch(r'[-—·]*(?:\d+|[ivxlcdmIVXLCDM]+)[-—·]*',text))))
    # Image source/drawing semantics; the digest is pixels, not compressed bytes.
    images=[]
    rels={n.get('Id'):n.get('Target') for n in o.parse_xml(parts[o.DOC_RELS])}
    for p in paragraphs:
        for drawing in p.iter(o.q(o.W,'drawing')):
            for blip in drawing.xpath('.//*[local-name()="blip"]'):
                rid=blip.get(o.q('http://schemas.openxmlformats.org/officeDocument/2006/relationships','embed'))
                target=rels.get(rid,'');record=dict(block_id=p.get(block_attribute),tight=bool(drawing.xpath('.//*[local-name()="wrapTight" or local-name()="wrapThrough"]')),crop=bool(drawing.xpath('.//*[local-name()="srcRect"]')),digest=None,alpha=None)
                try:
                    from PIL import Image
                    from posixpath import normpath
                    raw=parts[normpath('word/'+target)]
                    with Image.open(io.BytesIO(raw)) as image:
                        record['digest']=hashlib.md5(image.convert('RGB').tobytes()).digest()
                        if 'A' in image.getbands():record['alpha']=image.getchannel('A').copy()
                except (KeyError,OSError):pass
                images.append(record)
    import pymupdf as fitz
    for index,page in enumerate(pdf):
        spans=page_spans[index];area=region(page)
        for s in spans:
            box=fitz.Rect(s['bbox'])
            if furniture(s,page):continue
            if not page.rect.contains(box) and (box.x0 < -1 or box.y0 < -1 or box.x1>page.rect.width+1 or box.y1>page.rect.height+1):add('content_clipped',index+1,s['block_id'],dict(bbox=list(box),page=list(page.rect)))
            elif s['block_id'] and (box.x0<area.x0-3 or box.x1>area.x1+3 or box.y0<area.y0-3 or box.y1>area.y1+3):add('content_outside_margins',index+1,s['block_id'],dict(bbox=list(box),content_region=list(area)))
        for image in page.get_image_info(hashes=True):
            rect=fitz.Rect(image['bbox']);matched=[r for r in images if r['digest'] and r['digest']==image.get('digest')]
            rec=matched[0] if len(matched)==1 else images[0] if len(images)==1 else None
            block=rec['block_id'] if rec else None
            if block:placements[block].add(index+1)
            if not page.rect.contains(rect):add('image_clipped',index+1,block,dict(bbox=list(rect)))
            elif not area.contains(rect):add('image_outside_margins',index+1,block,dict(bbox=list(rect),content_region=list(area)))
            if design and design.get('components',{}).get('pagination',{}).get('preserve_image_aspect') and rec and not rec['crop']:
                aspect=(rect.width/max(rect.height,.1))/(image['width']/max(image['height'],1))
                if not .75<=aspect<=1.33:add('image_distortion',index+1,block,dict(aspect_ratio_factor=round(aspect,3)))
            for s in spans:
                if furniture(s,page):continue
                box=fitz.Rect(s['bbox']);intersection=box&rect
                if intersection.is_empty or intersection.width<2 or intersection.height<2 or intersection.get_area()<.2*max(box.get_area(),1):continue
                if rec and rec['tight'] and rec.get('alpha') is not None:
                    mask=rec['alpha'];w,h=mask.size
                    crop=mask.crop((max(0,int((intersection.x0-rect.x0)/rect.width*w)),max(0,int((intersection.y0-rect.y0)/rect.height*h)),min(w,int((intersection.x1-rect.x0)/rect.width*w)+1),min(h,int((intersection.y1-rect.y0)/rect.height*h)+1)))
                    histogram=crop.histogram();opaque=sum(histogram[32:])
                    if opaque<.2*max(crop.width*crop.height,1):continue
                add('text_image_collision',index+1,s['block_id'],dict(text=s['text'],text_bbox=list(box),image_bbox=list(rect),image_block_id=block),related=[b for b in (s['block_id'],block) if b])
        # Only independently identified text objects can collide. Normal mixed runs,
        # superscripts/subscripts and cell content are one semantic paragraph/table.
        for i,left in enumerate(spans):
            if not left['block_id']:continue
            a=fitz.Rect(left['bbox'])
            for right in spans[i+1:]:
                if not right['block_id'] or left['block_id']==right['block_id'] or (left['table'] and left['table']==right['table']):continue
                if furniture(left,page) or furniture(right,page):continue
                b=fitz.Rect(right['bbox']);hit=a&b
                if not hit.is_empty and hit.height>.5*min(a.height,b.height) and hit.width>3 and hit.get_area()>.25*min(a.get_area(),b.get_area()):
                    add('text_collision',index+1,left['block_id'],dict(first_bbox=list(a),second_bbox=list(b)),related=[left['block_id'],right['block_id']])
    # Validate actual row/header placement as well as OOXML protection. cantSplit
    # cannot guarantee that an over-height row will fit; never accept it on XML alone.
    full_text=norm(o.ptext(root))
    for table in root.iter(o.q(o.W,'tbl')):
        identity=table.get(block_attribute);rows=list(table.findall(o.q(o.W,'tr')))
        pages=set(placements.get(identity,set()))
        if not rows or len(pages)<2:continue
        complex_table=bool(table.xpath('.//w:tbl|.//w:gridSpan|.//w:vMerge',namespaces=ns))
        op=dict(type='repair_table_pagination',block_id=identity) if identity and not complex_table else None
        for row in rows:
            row_pages=set().union(*(placements.get(n.get(block_attribute),set()) for n in row.iter(o.q(o.W,'p'))))
            # Repeating header rows legitimately occur on every continuation page.
            if row.xpath('./w:trPr/w:tblHeader[not(@w:val="0" or @w:val="false")]',namespaces=ns):continue
            if len(row_pages)>1:add('table_row_split',min(row_pages),identity,dict(pages=sorted(row_pages)),op)
        header=[norm(o.ptext(p)) for p in rows[0].iter(o.q(o.W,'p')) if len(norm(o.ptext(p)))>=3]
        for page in sorted(pages)[1:]:
            text=norm(pdf[page-1].get_text())
            if header and not all(h in text for h in header):add('table_header_missing',page,identity,'Actual continued table has no repeated header',op)
    for page in pdf:
        for drawing in page.get_drawings():
            box=drawing.get('rect')
            # Table borders, math fraction bars and chart vectors are not text
            # collision objects. Only prove clipping beyond the physical sheet.
            if box is not None and (box.x0 < -1 or box.y0 < -1 or box.x1>page.rect.width+1 or box.y1>page.rect.height+1):
                add('vector_clipped',page.number+1,None,dict(bbox=list(box)))
    def page_label(number):
        section=section_for(number)
        if not section or not section['pages']:return str(number)
        numbering=section['node'].find(o.q(o.W,'pgNumType'))
        if numbering is None:return str(number)
        start=int(numbering.get(o.q(o.W,'start'),'1'));value=number-min(section['pages'])+start
        fmt=numbering.get(o.q(o.W,'fmt'),'decimal')
        if fmt not in ('lowerRoman','upperRoman'):return str(value)
        result='';remaining=value
        for n,letters in [(1000,'M'),(900,'CM'),(500,'D'),(400,'CD'),(100,'C'),(90,'XC'),(50,'L'),(40,'XL'),(10,'X'),(9,'IX'),(5,'V'),(4,'IV'),(1,'I')]:
            while remaining>=n:result+=letters;remaining-=n
        return result.lower() if fmt=='lowerRoman' else result
    components=(plan or {}).get('sections',[])
    for component in components:
        pages=set().union(*(placements.get(b,set()) for b in component['block_ids']))
        if (component.get('kind')=='cover' or component.get('single_page')) and len(pages)>1:
            ids=[b for b in component['block_ids'] if b in by_id]
            add('cover_overflow' if component.get('kind')=='cover' else 'component_overflow',min(pages),ids[-1] if ids else None,dict(pages=sorted(pages),component=component['id']),dict(type='keep_component',block_ids=ids,block_id=ids[-1]) if ids else None)
        if component.get('continued_label'):
            for b in component['block_ids']:
                if b in nodes and nodes[b].tag==o.q(o.W,'tbl') and len(placements[b])>1:
                    for page in sorted(placements[b])[1:]:
                        if component['continued_label'] not in pdf[page-1].get_text():add('continued_table_label_missing',page,b,component['continued_label'])
        numbering=component.get('numbering')
        if numbering and numbering['format']!='none' and not has_page_field:add('page_number_field_missing',min(pages) if pages else None,component['block_ids'][0],numbering)
        if numbering:
            for section in sections:
                if not set(component['block_ids']).intersection(section['blocks']):continue
                n=section['node'].find(o.q(o.W,'pgNumType'));actual=n.get(o.q(o.W,'fmt'),'decimal') if n is not None else 'decimal'
                start=n.get(o.q(o.W,'start'),'1') if n is not None else '1'
                if numbering['format']!='none' and (actual!=numbering['format'] or start!=str(numbering.get('start',1))):
                    anchor=next((b for b in reversed(section['blocks']) if b in by_id),None)
                    add('section_numbering',min(pages) if pages else None,anchor,dict(expected=numbering,actual_format=actual,actual_start=start),dict(type='repair_section_numbering',block_id=anchor,section_index=sections.index(section),format=numbering['format'],start=numbering.get('start',1)) if anchor else None)
    # TOC page fields are checked against heading destinations in the actual PDF.
    starts={b.get(o.q(o.W,'name')):b for b in root.iter(o.q(o.W,'bookmarkStart'))}
    for toc in root.xpath('//w:sdt[.//w:instrText[contains(text(),"TOC")]]',namespaces=ns):
        identity=toc.get(block_attribute);updates={};toc_pages=set()
        for p in toc.iter(o.q(o.W,'p')):toc_pages.update(placements.get(p.get(block_attribute),set()))
        fields=list(toc.iter(o.q(o.W,'fldSimple')))
        page_fields=[f for f in fields if re.match(r'\s*PAGEREF\s+',f.get(o.q(o.W,'instr'),''))]
        if not page_fields:add('toc_page_numbers_missing',min(toc_pages) if toc_pages else None,identity,'TOC has no PAGEREF results')
        for field in page_fields:
            bookmark=re.match(r'\s*PAGEREF\s+(\S+)',field.get(o.q(o.W,'instr'),''))[1]
            target=starts.get(bookmark);parent=target.getparent() if target is not None else None
            if parent is None:add('toc_target_missing',None,identity,bookmark);continue
            text=o.ptext(parent).strip();target_pages=[]
            expected=font_size(parent)
            for i,page in enumerate(pdf):
                hits=page.search_for(text)
                if hits and any(abs(s['size']-expected)<1 and norm(s['text']) in norm(text) for s in page_spans[i]):target_pages.append(i+1)
            if not target_pages:add('toc_target_unmapped',None,identity,bookmark);continue
            destination=target_pages[-1]
            # Match rendered entry row (right-aligned page number may be its own span).
            link=field.getparent();entry_text=''.join(t.text or '' for t in link.iter(o.q(o.W,'t')) if field not in t.iterancestors()) if link is not None else ''
            numeric=False
            for i,page in enumerate(pdf):
                for box in page.search_for(entry_text) if entry_text else []:
                    if abs((box.y1-box.y0)-(expected*1.4))<1 and i+1==destination:continue
                    row=[s['text'] for s in page_spans[i] if abs((s['bbox'][1]+s['bbox'][3])/2-(box.y0+box.y1)/2)<max(3,box.height*.45) and s['bbox'][0]>=box.x0-2]
                    if re.search(r'(?:\d+|[ivxlcdmIVXLCDM]+)$',norm(''.join(row))):numeric=True
            cached=o.ptext(field).strip()
            if not numeric or not cached or cached!=page_label(destination):updates[bookmark]=page_label(destination)
        if updates:add('toc_page_results',min(toc_pages) if toc_pages else None,identity,dict(expected=updates),dict(type='refresh_toc_pages',block_id=identity,pages=updates) if identity else None)
    # A TOC-looking paragraph with leader dots but no TOC/page field must not pass.
    for p in paragraphs:
        style=p.xpath('string(./w:pPr/w:pStyle/@w:val)',namespaces=ns)
        if style.startswith('TOC') and not p.xpath('.//w:fldSimple[contains(@w:instr,"PAGEREF")]|.//w:instrText[contains(text(),"PAGEREF")]',namespaces=ns) and not re.search(r'(?:\d+|[ivxlcdmIVXLCDM]+)\s*$',o.ptext(p)):
            add('toc_page_numbers_missing',min(placements.get(p.get(block_attribute),{0})) or None,p.get(block_attribute),'Leader dots are not page numbers')
    section_map=[dict(id=c['id'],kind=c.get('kind','body'),pages=sorted(set().union(*(placements.get(b,set()) for b in c['block_ids'])))) for c in components]
    return dict(findings=findings,block_pages={k:sorted(v) for k,v in placements.items()},section_pages=section_map,detectors=['text_image_collision','text_collision','content_regions','cover_pagination','toc_results','section_numbering','image_geometry','table_continuations'])
