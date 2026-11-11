"""Workflow helpers using the existing atomic engine, snapshots and rendering."""
import hashlib
import io
import json
from pathlib import Path
import time


def replay(store,c,state,request,a):
    a.identifier(request['operation_id'])
    if state is None or request['document_id']!=state['document_id']: raise ValueError('Document identity mismatch')
    old=c.execute('SELECT request,result FROM revisions WHERE operation_id=?',(request['operation_id'],)).fetchone()
    if old:
        if json.loads(old[0])!=request: raise ValueError('Operation ID reused with different payload')
        return json.loads(old[1])
    store.assert_current(state,request['base_revision'])


def save_plan(store,request,a):
    plan=request['plan']; a._sibling('document_plan').validate(plan)
    if plan['document_id']!=request['document_id']: raise ValueError('Plan document identity mismatch')
    with store.locked() as(c,state):
        previous=replay(store,c,state,request,a)
        if previous:return previous
        old_plan=state.get('document_plan') or {}
        old={s['id']:s for s in old_plan.get('sections',[])}
        new={s['id']:s for s in plan['sections']}
        affected={k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
        old_refs={r['id']:r['text'] for r in old_plan.get('references',[])}
        new_refs={r['id']:r['text'] for r in plan.get('references',[])}
        changed_refs={k for k in old_refs.keys()|new_refs.keys() if old_refs.get(k)!=new_refs.get(k)}
        affected.update(s['id'] for s in plan['sections'] if changed_refs.intersection(s.get('citations',[])))
        if old_plan.get('design')!=plan.get('design'):affected.update(new)
        affected=sorted(affected)
        state['document_plan']=plan
        statuses=state.setdefault('sections',{})
        for k in affected:
            statuses[k]=dict(status='needs_review',reason='plan_changed')
        return store.commit(c,state,store.path.read_bytes(),request['operation_id'],request,[],extra=dict(plan=plan,document_plan=plan,affected_sections=affected))


def apply_section(store,request,asset_root,a):
    limits=a._sibling('document_plan'); section_id=a.identifier(request['section_id'])
    ops=request['operations']
    if not isinstance(ops,list) or not 1<=len(ops)<=limits.MAX_OPERATIONS: raise ValueError('Section operation count exceeds limit')
    if len(json.dumps(ops,ensure_ascii=False))>limits.MAX_CHARACTERS: raise ValueError('Section character budget exceeded')
    with store.locked() as(c,state):
        previous=replay(store,c,state,request,a)
        if previous:return previous
        if state['gate']!='open':raise ValueError('Section checkpoint required: '+state['gate'])
        plan=state.get('document_plan')
        if not plan:raise ValueError('Save a validated document plan before apply-section')
        section=next((s for s in plan['sections'] if s['id']==section_id),None)
        if not section:raise ValueError('Section not in document plan')
        allowed=set(section['block_ids']); styles=set(section.get('styles',[]))
        # Global edits belong to apply-one, never to an allegedly local section transaction.
        global_ops={'set_page','set_header_footer','document.recolor','part.replace_text','section.clone'}
        parts=a.o.read_parts(store.path); changed=[]; started=time.monotonic()
        base=Path(asset_root or store.path.parent).resolve()
        resources=set(); resource_size=0
        for op in ops:
            if not isinstance(op,dict) or op.get('type') in global_ops or op.get('block_id') not in allowed:
                raise ValueError('Operation must target a planned section block')
            for key in ('source_block_id','after_block_id'):
                if op.get(key) and op[key] not in allowed: raise ValueError('Cross-section mutation or anchor is not allowed')
            if styles and op.get('style') and op['style'] not in styles:raise ValueError('Unplanned section style')
            # Include nested image-row resources; reject escape paths before reading bytes.
            def paths(value):
                if isinstance(value,dict):
                    for k,v in value.items():
                        if k=='path' and isinstance(v,str): yield v
                        else: yield from paths(v)
                elif isinstance(value,list):
                    for v in value: yield from paths(v)
            for name in paths(op):
                path=(base/name).resolve()
                if not path.is_relative_to(base) or not path.is_file():raise ValueError('Invalid section resource path')
                if path not in resources:
                    resources.add(path);resource_size+=path.stat().st_size
                if resource_size>limits.MAX_RESOURCE_BYTES:raise ValueError('Section resource budget exceeded')
            parts,ids,_=a.mutate(parts,op,base); changed.extend(ids)
            design=state.get('selected_design')
            if design and op.get('type') in ('append_table','insert_table'):
                document=a.o.parse_xml(parts[a.o.MAIN]); table=document.xpath('//*[@b:id=$id]',namespaces={'b':a.BLOCK_NS},id=op['block_id'])[0]
                pr=table.find(a.o.q(a.o.W,'tblPr'))
                if pr is None:pr=a.o.etree.Element(a.o.q(a.o.W,'tblPr'));table.insert(0,pr)
                pr.insert(0,a.o.etree.Element(a.o.q(a.o.W,'tblStyle'),{a.o.q(a.o.W,'val'):design['table']['style_id']}))
                # Native operations supply direct borders/fills. Map these too so
                # they do not override the selected named table style visually.
                for border in pr.findall('./'+a.o.q(a.o.W,'tblBorders')+'/*'):
                    border.set(a.o.q(a.o.W,'color'),design['table']['border_color'])
                for shade in table.xpath('./w:tr[1]//w:shd',namespaces=a.o.NS):
                    shade.set(a.o.q(a.o.W,'fill'),design['table']['header_fill'])
                parts[a.o.MAIN]=a.o.xml_bytes(document)
            if sum(len(v) for v in parts.values())>64*1024*1024:raise ValueError('Section package size exceeds limit')
        # Forward references resolve after the final mutation, not at intermediate steps.
        root=a.o.parse_xml(parts[a.o.MAIN]); unresolved=a._sibling('academic_blocks').refresh_fields(parts,root,a.o)
        parts[a.o.MAIN]=a.o.xml_bytes(root)
        findings=inspect_parts(parts,a)
        blocking=[f for f in findings if f['code'] in ('invalid_equation','broken_chart','broken_relationship','duplicate_bookmark')]
        if blocking:raise ValueError('Section structural validation failed: '+str(blocking))
        data=a.packed(parts)
        state.setdefault('sections',{})[section_id]=dict(status='generated',revision=state['revision']+1,block_ids=sorted(set(changed)))
        state['workflow_version']=1
        # One section, one checkpoint. Legacy apply-one retains its three-operation gate.
        state['gate']='checkpoint'
        result=store.commit(c,state,data,request['operation_id'],request,sorted(set(changed)),extra=dict(section_id=section_id,operation_count=len(ops),unresolved_references=unresolved,transaction_ms=round((time.monotonic()-started)*1000,2)))
        return result


def inspect_parts(parts,a):
    o=a.o;root=o.parse_xml(parts[o.MAIN]); issues=[]
    def add(code,node=None,operation=None,detail=''):
        current=node
        while current is not None and not current.get(a.BLOCK_ID):current=current.getparent()
        block=current.get(a.BLOCK_ID) if current is not None else None
        issues.append(dict(code=code,block_id=block,deterministic=operation is not None,operation=operation,detail=detail))
    validation=o.validate_parts(parts)
    for error in validation['errors']: add('broken_relationship',detail=str(error))
    style_root=o.parse_xml(parts.get('word/styles.xml', ('<w:styles xmlns:w="'+o.W+'"/>').encode()))
    styles={node.get(o.q(o.W,'styleId')):node for node in style_root}
    def effective_keep(p,style):
        direct=p.find('./'+o.q(o.W,'pPr')+'/'+o.q(o.W,'keepNext'))
        seen=set()
        while direct is None and style in styles and style not in seen:
            seen.add(style); node=styles[style]
            direct=node.find('./'+o.q(o.W,'pPr')+'/'+o.q(o.W,'keepNext'))
            style=node.xpath('string(./w:basedOn/@w:val)',namespaces=o.NS)
        return direct is not None and direct.get(o.q(o.W,'val')) not in ('0','false','off')
    previous_level=0
    for p in root.iter(o.q(o.W,'p')):
        style=p.xpath('string(./w:pPr/w:pStyle/@w:val)',namespaces=o.NS)
        import re
        match=re.fullmatch('[Hh]eading([1-9])',style)
        if match:
            level=int(match[1])
            if level>previous_level+1:add('heading_hierarchy',p,detail=f'Heading {previous_level} to {level}')
            previous_level=level
            if not effective_keep(p,style):
                add('heading_keep_next',p,dict(type='set_paragraph_format',block_id=p.get(a.BLOCK_ID),keep_next=True))
        if '{{ref:' in o.ptext(p) or '{{pageref:' in o.ptext(p):add('unresolved_reference',p)
    names=root.xpath('//w:bookmarkStart/@w:name',namespaces=o.NS)
    if len(names)!=len(set(names)):add('duplicate_bookmark')
    # Word REF fields must point to a real bookmark (TOC/PAGE are handled separately).
    import re
    for node in root.xpath('//w:instrText|//w:fldSimple',namespaces=o.NS):
        match=re.match(r'\s*(?:REF|PAGEREF)\s+([^\s\\]+)',node.get(o.q(o.W,'instr')) or node.text or '')
        if match and match[1] not in names:add('unresolved_reference',node,detail=match[1])
    math_ns='http://schemas.openxmlformats.org/officeDocument/2006/math'
    for equation in root.iter(o.q(math_ns,'oMath')):
        if not any((t.text or '').strip() for t in equation.iter(o.q(math_ns,'t'))):add('invalid_equation',equation)
    for name,data in parts.items():
        if name.startswith('word/charts/') and name.endswith('.xml'):
            chart=o.parse_xml(data)
            if not chart.xpath('//*[local-name()="ser"]'):add('broken_chart',detail=name)
    for table in root.iter(o.q(o.W,'tbl')):
        rows=list(table.findall(o.q(o.W,'tr')))
        if len(rows)>10:
            bad=any(not tr.xpath('./w:trPr/w:cantSplit[not(@w:val="0" or @w:val="false" or @w:val="off")]',namespaces=o.NS) for tr in rows)
            bad=bad or bool(table.xpath('.//w:pPr/w:keepNext[not(@w:val="0" or @w:val="false" or @w:val="off")]',namespaces=o.NS))
            first=rows[0].find('./'+o.q(o.W,'trPr')+'/'+o.q(o.W,'tblHeader'))
            if bad or first is None or first.get(o.q(o.W,'val')) in ('0','false','off'):
                complex_table=bool(table.xpath('.//w:tbl|.//w:gridSpan|.//w:vMerge',namespaces=o.NS))
                add('long_table_pagination',table,None if complex_table else dict(type='repair_table_pagination',block_id=table.get(a.BLOCK_ID)),detail='Complex table requires lossless manual review' if complex_table else '')
    return issues


def check_document(store,final,a,section_id=None):
    started=time.monotonic();current=store.status();revision=current['revision']
    plan=current.get('document_plan')
    if section_id and (not plan or section_id not in {s['id'] for s in plan['sections']}):raise ValueError('Unknown section')
    parts=a.o.read_parts(io.BytesIO(store.snapshot(revision)))
    findings=inspect_parts(parts,a)
    event=store.checkpoint(final)
    if event['revision']!=revision:raise ValueError('Revision conflict during document check')
    for page in event['pages']:
        checks=page['checks']
        for code in ('content_overflow','table_split','heading_orphan','margins_abnormal','blank_page','widow_orphan'):
            if code=='widow_orphan' and checks.get(code) and page.get('widow_blocks'):
                for block in sorted(set(page['widow_blocks'])):
                    findings.append(dict(code=code,page=page['page'],block_id=block,deterministic=True,operation=dict(type='set_paragraph_format',block_id=block,widow_control=True),detail='One paragraph line isolated across page boundary'))
                continue
            if checks.get(code):findings.append(dict(code=code,page=page['page'],block_id=page.get('block_ids',[None])[0] if len(page.get('block_ids',[]))==1 else None,block_ids=page.get('block_ids',[]),deterministic=False,operation=None,detail='Inspect actual page geometry'))
        if checks.get('fonts_missing'):findings.append(dict(code='fonts_missing',page=page['page'],block_id=None,deterministic=False,operation=None,detail=checks['fonts_missing']))
    plan=current.get('document_plan')
    if section_id and (not plan or section_id not in {s['id'] for s in plan['sections']}):raise ValueError('Unknown section')
    if final and plan:
        document=a.o.parse_xml(parts[a.o.MAIN])
        nodes={b.get(a.BLOCK_ID):b for b in document.iter() if b.get(a.BLOCK_ID)}
        ids=set(nodes)
        known_styles={n.get(a.o.q(a.o.W,'styleId')) for n in a.o.parse_xml(parts['word/styles.xml'])}
        for section in plan['sections']:
            for block in set(section['block_ids'])-ids:findings.append(dict(code='missing_planned_block',block_id=block,deterministic=False,operation=None,detail=section['id']))
            for style in set(section.get('styles',[]))-known_styles:
                findings.append(dict(code='missing_planned_style',block_id=None,deterministic=False,operation=None,detail=style))
            for key,tag in [('equations','oMath'),('figures','drawing'),('tables','tbl')]:
                for block in section.get(key,[]):
                    node=nodes.get(block)
                    if node is not None and not any(a.o.etree.QName(n).localname==tag for n in node.iter()):
                        findings.append(dict(code='planned_resource_type',block_id=block,deterministic=False,operation=None,detail=key))
    targets=[]
    for finding in findings:
        finding['target_id']=hashlib.sha256(json.dumps(finding,sort_keys=True).encode()).hexdigest()[:24]
        targets.append(finding)
    result=dict(document_id=current['document_id'],revision=revision,structure_passed=not any(f['code'] not in {'content_overflow','table_split','heading_orphan','margins_abnormal','blank_page','widow_orphan','fonts_missing'} for f in findings),layout_passed=not event['render_error'] and bool(event['pages']) and all(p['checks']['automatic_passed'] for p in event['pages']),repair_targets=targets,render_error=event['render_error'],pages=event['pages'],scope=section_id or 'document',duration_ms=round((time.monotonic()-started)*1000,2))
    result['final']=final
    result['passed']=not targets and result['layout_passed']
    with store.locked() as(c,state):
        store.assert_current(state,revision)
        state['document_check']=result
        if not result['passed']:state['gate']='failed'
        if section_id:state.setdefault('sections',{}).setdefault(section_id,{})['status']='checked' if result['passed'] else 'failed'
        store.save_state(c,state)
        c.execute('INSERT INTO events(data) VALUES (?)',(json.dumps(dict(type='document_checked',document_id=state['document_id'],revision=revision,path=store.path.name,gate=state['gate'],document_check=result)),))
        c.commit()
    return result


def repair_document(store,base_revision,operation_id,a):
    state=store.status()
    # A retry after a committed repair remains idempotent even if rechecking crashed.
    with store.locked() as(c,current):
        previous=c.execute('SELECT request,result FROM revisions WHERE operation_id=?',(operation_id,)).fetchone()
        if previous:
            req=json.loads(previous[0])
            if req.get('repair')!=base_revision:raise ValueError('Operation ID reused')
            committed=json.loads(previous[1])
        else:committed=None
    if committed:return dict(committed,recheck=check_document(store,True,a))
    check=state.get('document_check')
    if not check or check['revision']!=base_revision or state['revision']!=base_revision:raise ValueError('A current check-document is required')
    operations=[]
    for target in check['repair_targets']:
        if target['deterministic'] and target.get('block_id') and target.get('operation') not in operations:operations.append(target['operation'])
    if not operations:return dict(status='unrepairable',revision=base_revision,remaining=check['repair_targets'])
    a.identifier(operation_id)
    with store.locked() as(c,state):
        store.assert_current(state,base_revision)
        parts=a.o.read_parts(store.path);changed=[]
        for op in operations:
            if op['type']=='repair_table_pagination':
                root=a.o.parse_xml(parts[a.o.MAIN]);matches=root.xpath('//*[@b:id=$id]',namespaces={'b':a.BLOCK_NS},id=op['block_id'])
                if len(matches)!=1:raise ValueError('Repair target no longer exists')
                table=matches[0]
                for i,tr in enumerate(table.iter(a.o.q(a.o.W,'tr'))):
                    pr=tr.find(a.o.q(a.o.W,'trPr'))
                    if pr is None:pr=a.o.etree.Element(a.o.q(a.o.W,'trPr'));tr.insert(0,pr)
                    for tag in ('cantSplit','tblHeader') if i==0 else ('cantSplit',):
                        control=pr.find(a.o.q(a.o.W,tag))
                        if control is None:control=a.o.etree.SubElement(pr,a.o.q(a.o.W,tag))
                        control.set(a.o.q(a.o.W,'val'),'1')
                for p in table.iter(a.o.q(a.o.W,'p')):a.o.set_para_format(p,dict(keep_next=False))
                parts[a.o.MAIN]=a.o.xml_bytes(root)
            else:parts,_,_=a.mutate(parts,op,store.path.parent)
            changed.append(op['block_id'])
        result=store.commit(c,state,a.packed(parts),operation_id,dict(repair=base_revision),changed,extra=dict(repaired=len(operations),attempted=len(check['repair_targets'])))
    return dict(result,recheck=check_document(store,True,a))
