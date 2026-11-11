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
            design=state.get('selected_design')
            if design and design.get('version',1)>=2 and design['page'].get('columns',1)==2:
                # Size only unspecified new components to the actual text column.
                # Explicit user dimensions remain authoritative and are audited.
                import copy
                op=copy.deepcopy(op)
                width=a._sibling('academic_blocks')._text_width(a.o.parse_xml(parts[a.o.MAIN]),a.o)
                if op['type']=='insert_chart' and 'width_cm' not in op.get('chart',{}):
                    chart=op.setdefault('chart',{});chart['width_cm']=round(width/567,2)
                    chart.setdefault('height_cm',round(chart['width_cm']*8/14,2))
                elif op['type']=='insert_image':op.setdefault('width_cm',round(width/567,2))
                elif op['type']=='append_table' and 'column_widths_twips' not in op:
                    count=max(len(row) for row in op['rows']);op['column_widths_twips']=[width//count]*count
            parts,ids,_=a.mutate(parts,op,base); changed.extend(ids)
            if design and design.get('version',1)>=2 and op['type']=='insert_equation':
                document=a.o.parse_xml(parts[a.o.MAIN]);node=document.xpath('//*[@b:id=$id]',namespaces={'b':a.BLOCK_NS},id=op['block_id'])[0]
                prop=node.find(a.o.q(a.o.W,'pPr'))
                if prop is None:prop=a.o.etree.Element(a.o.q(a.o.W,'pPr'));node.insert(0,prop)
                prop.insert(0,a.o.etree.Element(a.o.q(a.o.W,'pStyle'),{a.o.q(a.o.W,'val'):'Equation'}))
                parts[a.o.MAIN]=a.o.xml_bytes(document)
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
                if design.get('version',1)>=2:
                    for paragraph in table.iter(a.o.q(a.o.W,'p')):
                        ppr=paragraph.find(a.o.q(a.o.W,'pPr'))
                        if ppr is None:ppr=a.o.etree.Element(a.o.q(a.o.W,'pPr'));paragraph.insert(0,ppr)
                        style=ppr.find(a.o.q(a.o.W,'pStyle'))
                        if style is None:style=a.o.etree.SubElement(ppr,a.o.q(a.o.W,'pStyle'))
                        style.set(a.o.q(a.o.W,'val'),'TableText')
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
    findings.extend(a._sibling('template_styles').design_deviations(parts,current.get('selected_design'),a.o,a.BLOCK_ID))
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
    geometry={}
    if final and not event['render_error']:
        import pymupdf as fitz
        with fitz.open(store.render_directory(revision)/'preview.pdf') as pdf:
            geometry=a._sibling('layout_review').inspect(parts,pdf,a.o,a.BLOCK_ID,plan,current.get('selected_design'))
        findings.extend(geometry['findings'])
        for page in event['pages']:
            page['block_ids']=sorted(set(page.get('block_ids',[]))|{b for b,pages in geometry['block_pages'].items() if page['page'] in pages})
    targets=[]
    for finding in findings:
        finding.update(revision=revision,severity=finding.get('severity','error'),repairable=finding.get('deterministic',False),page=finding.get('page'))
        finding['target_id']=hashlib.sha256(json.dumps(finding,sort_keys=True).encode()).hexdigest()[:24]
        targets.append(finding)
    result=dict(document_id=current['document_id'],revision=revision,structure_passed=not any(f['code'] not in {'content_overflow','table_split','heading_orphan','margins_abnormal','blank_page','widow_orphan','fonts_missing'} for f in findings),layout_passed=not event['render_error'] and bool(event['pages']) and all(p['checks']['automatic_passed'] for p in event['pages']),repair_targets=targets,render_error=event['render_error'],pages=event['pages'],scope=section_id or 'document',duration_ms=round((time.monotonic()-started)*1000,2))
    layout_codes={'text_image_collision','text_collision','content_clipped','content_outside_margins','image_clipped','image_outside_margins','image_distortion','cover_overflow','component_overflow','table_row_split','table_header_missing','vector_clipped'}
    if any(t['code'] in layout_codes for t in targets):result['layout_passed']=False
    result['geometry']=geometry
    result['collision_check_executed']=bool(final and geometry)
    result['final']=final
    result['passed']=not targets and result['layout_passed']
    with store.locked() as(c,state):
        store.assert_current(state,revision)
        state['document_check']=result
        state['pages']=result['pages']
        if result['passed'] and state.get('repair_summary'):state['repair_summary'].update(remaining=[],exhausted=False)
        if not result['passed']:state.update(gate='failed',finalized=False)
        state['delivery_status']='draft_pending_visual' if result['passed'] else 'draft_failed_layout'
        if final and current.get('quality_contract',1)>=2:
            prior=state.get('visual_request') or {}
            fingerprints=[p['fingerprint'] for p in result['pages']]
            if prior.get('revision')==revision and prior.get('fingerprints')==fingerprints:
                state['visual_request']=dict(prior,eligible=result['passed'])
            else:
                import uuid
                state['visual_request']=dict(document_id=state['document_id'],revision=revision,sha256=state['sha256'],fingerprints=fingerprints,eligible=result['passed'],request_id=uuid.uuid4().hex)
        state['delivery']=a._sibling('quality_status').delivery(state)
        state['delivery_status']=state['delivery']['status']
        if section_id:state.setdefault('sections',{}).setdefault(section_id,{})['status']='checked' if result['passed'] else 'failed'
        store.save_state(c,state)
        c.execute('INSERT INTO events(data) VALUES (?)',(json.dumps(dict(type='document_checked',document_id=state['document_id'],revision=revision,path=store.path.name,gate=state['gate'],document_check=result,delivery_status=state['delivery_status'],visual_request=state.get('visual_request'),delivery=state['delivery'],finalized=state.get('finalized',False),selected_design=state.get('selected_design'))),))
        c.commit()
    return result


def _repair_once(store,base_revision,operation_id,a):
    state=store.status()
    # A retry after a committed repair remains idempotent even if rechecking crashed.
    with store.locked() as(c,current):
        previous=c.execute('SELECT request,result FROM revisions WHERE operation_id=?',(operation_id,)).fetchone()
        if previous:
            req=json.loads(previous[0])
            if req.get('repair')!=base_revision:raise ValueError('Operation ID reused')
            committed=json.loads(previous[1])
        else:committed=None
    if committed:
        if committed['revision']!=state['revision']:raise ValueError('Revision conflict after interrupted repair')
        return dict(committed,recheck=check_document(store,True,a))
    check=state.get('document_check')
    if not check or check['revision']!=base_revision or state['revision']!=base_revision:raise ValueError('A current check-document is required')
    operations=[]
    for target in check['repair_targets']:
        if target['deterministic'] and target.get('block_id') and target.get('operation') not in operations:operations.append(target['operation'])
    operations.sort(key=lambda op:op['type']=='refresh_toc_pages')
    if not operations:return dict(status='unrepairable',revision=base_revision,remaining=check['repair_targets'])
    a.identifier(operation_id)
    with store.locked() as(c,state):
        store.assert_current(state,base_revision)
        parts=a.o.read_parts(store.path);changed=[]
        for op in operations:
            if op['type'] in ('keep_component','refresh_toc_pages','repair_section_numbering'):
                root=a.o.parse_xml(parts[a.o.MAIN])
                if op['type']=='keep_component':
                    for i,block in enumerate(op['block_ids']):
                        matches=root.xpath('//*[@b:id=$id]',namespaces={'b':a.BLOCK_NS},id=block)
                        if len(matches)!=1 or matches[0].tag!=a.o.q(a.o.W,'p'):raise ValueError('Component repair requires paragraph blocks')
                        a.o.set_para_format(matches[0],dict(keep_next=i<len(op['block_ids'])-1,keep_lines=True,space_before_twips=0,space_after_twips=120))
                elif op['type']=='refresh_toc_pages':
                    targets=root.xpath('//*[@b:id=$id]',namespaces={'b':a.BLOCK_NS},id=op['block_id'])
                    if len(targets)!=1:raise ValueError('TOC repair target missing')
                    import re
                    for field in targets[0].iter(a.o.q(a.o.W,'fldSimple')):
                        match=re.match(r'\s*PAGEREF\s+(\S+)',field.get(a.o.q(a.o.W,'instr'),''))
                        if match and match[1] in op['pages']:
                            a._sibling('academic_blocks')._set_cached(field,a.o,op['pages'][match[1]])
                else:
                    sections=list(root.iter(a.o.q(a.o.W,'sectPr')));target=sections[op['section_index']]
                    n=target.find(a.o.q(a.o.W,'pgNumType'))
                    if n is None:n=a.o.etree.SubElement(target,a.o.q(a.o.W,'pgNumType'))
                    n.set(a.o.q(a.o.W,'fmt'),op['format']);n.set(a.o.q(a.o.W,'start'),str(op['start']))
                parts[a.o.MAIN]=a.o.xml_bytes(root)
            elif op['type']=='repair_table_pagination':
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



def repair_document(store,base_revision,operation_id,a,max_attempts=3):
    if type(max_attempts) is not int or not 1<=max_attempts<=3:raise ValueError('Repair loop limit is 1-3')
    a.identifier(operation_id)
    with store.locked() as(c,state):
        old=(state.get('repair_runs') or {}).get(operation_id)
        if old and (old['base_revision']!=base_revision or old['limit']!=max_attempts):raise ValueError('Repair operation ID reused')
        if old and old.get('done'):return old['result']
        run=old or dict(base_revision=base_revision,limit=max_attempts,attempts=[])
        if not old:store.assert_current(state,base_revision)
        state.setdefault('repair_runs',{})[operation_id]=run;store.save_state(c,state);c.commit()
    result=None
    for i in range(max_attempts):
        current=store.status();check=current.get('document_check')
        if not check or check['revision']!=current['revision']:check=check_document(store,True,a)
        if check['passed'] and i>=len(run.get('steps',[])):
            result=dict(status='checked',revision=current['revision'],recheck=check,repaired=0);break
        opid=operation_id if i==0 else operation_id[:60]+'-retry-'+str(i)
        with store.locked() as(c,state):
            item=state['repair_runs'][operation_id]
            steps=item.setdefault('steps',[])
            if i>=len(steps):
                store.assert_current(state,current['revision'])
                steps.append(dict(base_revision=current['revision'],operation_id=opid))
            step=steps[i];run=item
            store.save_state(c,state);c.commit()
        result=_repair_once(store,step['base_revision'],step['operation_id'],a)
        if result.get('status')=='unrepairable':break
        with store.locked() as(c,state):
            item=state['repair_runs'][operation_id]
            if result['revision'] not in [r['revision'] for r in item['attempts']]:item['attempts'].append(dict(revision=result['revision'],operation_id=opid,repaired=result.get('repaired',0)))
            store.save_state(c,state);c.commit()
        if result['recheck']['passed']:break
    latest=store.status();check=latest.get('document_check') or {}
    result=dict(result or {},revision=latest['revision'],recheck=check,repair_attempts=len(latest['repair_runs'][operation_id]['attempts']),remaining=check.get('repair_targets',[]),exhausted=not check.get('passed',False))
    with store.locked() as(c,state):
        store.assert_current(state,latest['revision'])
        state['repair_runs'][operation_id].update(done=True,result=result)
        state['repair_summary']=dict(attempts=sum(len(r['attempts']) for r in state['repair_runs'].values()),remaining=result['remaining'],exhausted=result['exhausted'])
        store.save_state(c,state);c.commit()
    return result
