#!/usr/bin/env python3
"""Reproducible real-render acceptance for section-based DOCX authoring.

Records tool-equivalent invocations, revisions, render cost and repair results.
Pages flow naturally; --page-target never inserts page breaks. Model status is
reported separately and never fabricated by this benchmark.
"""
import argparse
import importlib.util
import json
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('benchmark_workflow_engine',ROOT/'docx-ooxml-skill/scripts/atomic_docx.py')
a=importlib.util.module_from_spec(spec);spec.loader.exec_module(a)

TOPICS=[('Scope and evidence','Define observable outcomes and establish a reproducible evidence baseline.'),
        ('Data collection','Measure source quality, coverage, completeness and the limits of each observation.'),
        ('Method and assumptions','Document model assumptions, compare alternatives and justify the selected approach.'),
        ('Evaluation protocol','Separate experimental observations from assumptions and describe the evaluation protocol.'),
        ('Results and uncertainty','Report uncertainty alongside measured effects and compare baseline performance.'),
        ('Reliability and recovery','Explain concurrency control, immutable snapshots and failure recovery boundaries.'),
        ('Implementation guidance','Translate evidence into specific implementation steps and verifiable outcomes.'),
        ('Conclusions and references','Connect the conclusions to evidence and identify remaining research questions.'),
        ('Operational controls','Document monitoring, maintenance and responsible owners for operational controls.'),
        ('Reproducibility appendix','Preserve the methods, inputs and evaluation criteria for independent replication.')]


def content(case,sections,paragraphs):
    all_ops=[];planned=[]
    for index in range(sections):
        topic,description=TOPICS[index%len(TOPICS)];prefix=f's{index+1}'
        operations=[]
        if index==0:operations.append(dict(type='insert_toc',block_id='toc',levels=3))
        operations.append(dict(type='append_paragraph',block_id=prefix+'-h',style='Heading1',text=f'{index+1}. {topic}',ref_id=prefix+'-heading'))
        operations.append(dict(type='append_paragraph',block_id=prefix+'-h2',style='Heading2',text=f'{index+1}.1 Evidence and method'))
        for j in range(paragraphs):
            text=f'{topic}, observation {index+1}.{j+1}. {description} '
            text+=' '.join([
                'The evaluation records the input, expected result and observed limitation so that another team can reproduce the decision.',
                'Each measurement is compared with its baseline under the same operating conditions and sampling window.',
                'A change is accepted only after its effects have been checked against the agreed requirements and evidence.',
                'Dependencies and resource relationships are recorded explicitly to support subsequent investigation and local correction.',
                'The conclusion remains conditional on the available evidence, with unresolved questions documented for later review.',
            ])
            operations.append(dict(type='append_paragraph',block_id=f'{prefix}-p{j}',text=text))
        if case=='academic':
            operations.extend([
                dict(type='insert_equation',block_id=prefix+'-eq',latex=r'\bar{x}=\frac{1}{n}\sum_{i=1}^{n}x_i',numbered=True,ref_id=prefix+'-eq-ref'),
                dict(type='insert_chart',block_id=prefix+'-chart',chart=dict(type='column',title=topic,categories=['Baseline','Observed','Target'],series=[dict(name='Quality (%)',values=[65+index,80+index,95])])),
                dict(type='insert_caption',block_id=prefix+'-cap',label='Figure',text=f'{topic}: quality comparison',ref_id=prefix+'-figure'),
                dict(type='append_paragraph',block_id=prefix+'-refs',text=f'As shown in {{{{ref:{prefix}-figure}}}}, the mean follows equation {{{{ref:{prefix}-eq-ref}}}}. Source [methodology].'),
            ])
        else:
            operations.extend([
                dict(type='append_paragraph',block_id=prefix+'-h3',style='Heading3',text=f'{index+1}.1.1 Verification matrix'),
                dict(type='append_table',block_id=prefix+'-table',rows=[['Control','Verification procedure','Expected evidence']]+[
                    [f'{prefix} control {j+1}',f'Check snapshot integrity and revision consistency for observation {j+1}.',f'Retain the measured outcome and the owning team for {prefix}-{j+1}.'] for j in range(59)],column_widths_twips=[1700,3800,3300],keep_together=False)])
        blocks=[op['block_id'] for op in operations]
        planned.append(dict(id=prefix,title=topic,requirements=description,block_ids=blocks,
            equations=[prefix+'-eq'] if case=='academic' else [],figures=[prefix+'-chart'] if case=='academic' else [],
            tables=[prefix+'-table'] if case=='technical' else [],citations=['methodology'],styles=['Normal','Heading1','Heading2','Heading3']))
        all_ops.append(operations)
    return planned,all_ops


def run(output,case,sections,paragraphs,page_target):
    output.mkdir(parents=True,exist_ok=True);calls=[]
    def call(command,fn):
        start=time.monotonic();result=fn()
        calls.append(dict(command=command,revision=result.get('revision'),duration_ms=round((time.monotonic()-start)*1000,2)))
        return result
    store=a.DocumentStore(output/f'{case}.docx')
    call('init',lambda:store.init('report',design=case))
    planned,operations=content(case,sections,paragraphs)
    plan=dict(version=1,document_id='report',title=f'{case} acceptance report',page_target=page_target,sections=planned,references=[dict(id='methodology',text='Acceptance benchmark methodology; repository fixture.')])
    (output/'document-plan.json').write_text(json.dumps(plan,indent=2))
    call('validate-plan',lambda:a._sibling('document_plan').validate(plan))
    call('save-plan',lambda:store.save_plan(dict(document_id='report',base_revision=0,operation_id='plan',plan=plan)))
    for i,ops in enumerate(operations):
        state=store.status()
        if state['gate']!='open':
            raise RuntimeError('Previous section failed: '+json.dumps(state.get('document_check')))
        payload=dict(document_id='report',base_revision=state['revision'],operation_id=f'section-{i+1}',section_id=f's{i+1}',operations=ops)
        (output/f'section-{i+1}.json').write_text(json.dumps(payload,indent=2))
        call('apply-section',lambda:store.apply_section(payload,output))
    check=call('check-document --final',lambda:store.check_document(final=True))
    repaired=0
    if any(t['deterministic'] for t in check['repair_targets']):
        repair=call('repair-document',lambda:store.repair_document(store.status()['revision'],'repair-final'))
        repaired=repair.get('repaired',0);check=repair.get('recheck',check)
    state=store.status()
    if check['passed']:call('finalize',lambda:store.finalize(state['revision']))
    # Legacy protocol: init, one call per atomic op, checkpoint per 3 ops,
    # final check and finalize. This is an exact protocol count, not model timing.
    atomics=sum(len(ops) for ops in operations)
    legacy_calls=1+atomics+(atomics+2)//3+2
    summary=dict(case=case,page_target=page_target,actual_pages=len(check['pages']),passed=check['passed'],
        new_tool_calls=len(calls),legacy_protocol_calls=legacy_calls,call_reduction=round(1-len(calls)/legacy_calls,4),
        revision=state['revision'],calls=calls,repair_successes=repaired,repair_targets=check['repair_targets'],
        visual_review='pending; requires configured host vision service',editable=True,forced_page_breaks=False)
    assert summary['call_reduction']>=.5
    assert a.o.validate_parts(a.o.read_parts(store.path))['ok']
    from docx import Document
    Document(store.path)
    (output/'acceptance.json').write_text(json.dumps(summary,indent=2))
    return summary


def run_legacy(output,case,sections,paragraphs,page_target):
    """Execute the unchanged apply-one/three-dirty-operation checkpoint protocol."""
    output.mkdir(parents=True,exist_ok=True)
    store=a.DocumentStore(output/f'{case}-legacy.docx');calls=[]
    def call(command,fn):
        start=time.monotonic();result=fn()
        calls.append(dict(command=command,revision=result.get('revision'),duration_ms=round((time.monotonic()-start)*1000,2)))
        return result
    call('init',lambda:store.init('report',design=case))
    _,batches=content(case,sections,paragraphs)
    for ops in batches:
        for op in ops:
            state=store.status()
            if state['gate']!='open':
                checked=call('checkpoint',store.checkpoint)
                if checked['gate']!='open':raise RuntimeError('Legacy checkpoint failed: '+json.dumps(checked))
                state=store.status()
            payload=dict(document_id='report',base_revision=state['revision'],operation_id=f'atomic-{state["revision"]+1}',operation=op)
            call('apply-one',lambda:store.apply_one(payload,output))
    checked=call('checkpoint --final',lambda:store.checkpoint(final=True))
    # Legacy publication still requires real manual visual evidence. Record the
    # command and its pending outcome; never forge approval to complete a count.
    start=time.monotonic()
    try:store.finalize(store.status()['revision'])
    except ValueError:pass
    calls.append(dict(command='finalize',outcome='visual_pending',duration_ms=round((time.monotonic()-start)*1000,2)))
    result=dict(case=case,protocol='legacy apply-one',actual_tool_calls=len(calls),actual_pages=len(checked['pages']),
        automatic_passed=all(p['checks']['automatic_passed'] for p in checked['pages']),revision=store.status()['revision'],calls=calls)
    (output/'legacy-acceptance.json').write_text(json.dumps(result,indent=2))
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,required=True);p.add_argument('--case',choices=['academic','technical'],required=True)
    p.add_argument('--legacy',action='store_true');p.add_argument('--sections',type=int,default=8);p.add_argument('--paragraphs',type=int,default=8);p.add_argument('--page-target',type=int,default=20)
    args=p.parse_args();print(json.dumps((run_legacy if args.legacy else run)(args.output,args.case,args.sections,args.paragraphs,args.page_target),indent=2))
