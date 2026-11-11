#!/usr/bin/env python3
"""Real-render 20–40 page research acceptance; optional REAL host vision via key prompt.

No verdicts are injected. Model-unavailable and model issues stay drafts. Secrets
are read with getpass and never serialized. Work/state is outside distributable files.
"""
import argparse
import getpass
import importlib.util
import json
import os
from pathlib import Path
import shutil
import sys
import time

ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
def load(name,path):
    spec=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m

def run(args):
    os.environ['LANGCHAIN_TRACING_V2']='false'
    adapter=load('accept_research_adapter',ROOT/'docx-ooxml-skill/platform_adapter.py')
    fixture=load('accept_research_fixture',ROOT/'scripts/benchmark_docx_workflow.py')
    args.output.mkdir(parents=True,exist_ok=True);files=args.output/'files';files.mkdir(exist_ok=True)
    store=adapter.DocumentStore(files/'research.docx');calls=[]
    def call(name,fn):
        started=time.monotonic();result=fn();calls.append(dict(command=name,revision=result.get('revision'),duration_ms=round((time.monotonic()-started)*1000,2)));print(name,result.get('revision'),flush=True);return result
    def request(opid,**data):return dict(document_id='research',base_revision=store.metadata()['revision'],operation_id=opid,**data)
    if not args.review_existing:
        call('init',lambda:store.init('research',design='cn-engineering-thesis'))
        sections,batches=fixture.content('academic',args.sections,args.paragraphs)
        cover=dict(id='cover',title='科研报告封面',requirements='封面日期与标题同页',kind='cover',block_ids=['cover-title','cover-date'])
        abstract=dict(id='abstract',title='摘要',requirements='摘要与关键词',kind='abstract',block_ids=['abstract-h','abstract-p','abstract-keys'])
        toc=dict(id='toc-section',title='目录',requirements='字段与实际页码',kind='toc',block_ids=['toc'])
        batches[0]=[op for op in batches[0] if op['block_id']!='toc'];sections[0]['block_ids'].remove('toc')
        for section in sections:section['kind']='body'
        # Semantic component starts, never one artificial break per target page.
        batches[0].insert(1,dict(type='set_paragraph_format',block_id='s1-h',page_break_before=True))
        table_rows=[['Control identifier','Verification procedure','Expected evidence']]+[[f'Run-{i:03d}',f'Measure reproducible observation {i:03d} under the baseline conditions.',f'Retain the measured outcome for protocol control {i:03d}.'] for i in range(1,60)]
        table_section=dict(id='matrix',title='验证矩阵',requirements='跨页重复表头、不拆行',kind='body',block_ids=['matrix-h','matrix-table'],tables=['matrix-table'])
        references=dict(id='references',title='参考文献',requirements='标注测试资料来源',kind='references',block_ids=['refs-h','refs-p'])
        plan=dict(version=1,document_id='research',title='科研质量验收报告',page_target=30,design='cn-engineering-thesis',sections=[cover,abstract,toc]+sections+[table_section,references],references=[dict(id='methodology',text='Acceptance benchmark methodology; repository fixture, not an external research citation.')])
        call('validate-plan',lambda:adapter.engine._sibling('document_plan').validate(plan))
        call('save-plan',lambda:store.save_plan(request('plan',plan=plan)))
        batches=[[
          dict(type='append_paragraph',block_id='cover-title',style='CoverTitle',text='科研文档质量验收报告'),
          dict(type='set_paragraph_format',block_id='cover-title',space_after_twips=14000),
          dict(type='append_paragraph',block_id='cover-date',style='CoverDate',text='2026 年 11 月 11 日')],
          [dict(type='append_paragraph',block_id='abstract-h',style='AbstractTitle',text='摘要'),dict(type='set_paragraph_format',block_id='abstract-h',page_break_before=True),dict(type='append_paragraph',block_id='abstract-p',style='AbstractBody',text='本报告用于验证可编辑科研文档的章节事务、公式图表、跨页表格、目录与质量检查闭环。报告内容是可复现的软件测试资料，不作为实际科研结论。确定性检查定位问题后仅局部修复，逐页与整稿视觉审查由后台模型独立执行。'),dict(type='append_paragraph',block_id='abstract-keys',text='关键词：可编辑文档；局部修复；质量验收')],
          [dict(type='insert_toc',block_id='toc',levels=3)]]+batches+[
          [dict(type='append_paragraph',block_id='matrix-h',style='Heading1',text=f'{args.sections+1}. Verification matrix'),dict(type='append_table',block_id='matrix-table',rows=table_rows,column_widths_twips=[1800,3800,3300],keep_together=False)],
          [dict(type='append_paragraph',block_id='refs-h',style='Heading1',text=f'{args.sections+2}. References'),dict(type='append_paragraph',block_id='refs-p',style='Reference',text='[1] Repository acceptance fixture. Research document quality methodology. 2026. Synthetic test data, not a published research source.')]]
        for section,ops in zip(plan['sections'],batches):
            call('apply-section '+section['id'],lambda section=section,ops=ops:store.apply_section(request('section-'+section['id'],section_id=section['id'],operations=ops),args.output))
        diagnostic=call('check-document --final --diagnostic-only',lambda:store.check_document(final=True,auto_repair=False))
        check=call('check-document --final',lambda:store.check_document(final=True))
        summary=dict(actual_pages=len(check['pages']),deterministic_passed=check['passed'],injected_findings=sorted({t['code'] for t in diagnostic['repair_targets']}),repair_summary=store.metadata().get('repair_summary'),unresolved=check['repair_targets'],calls=calls,soft_page_target=True)
        (args.output/'document-plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2)+'\n')
        if not check['passed']:
            (args.output/'acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');raise RuntimeError('Deterministic findings remain; see acceptance.json')

    else:
        summary=json.loads((args.output/'acceptance.json').read_text());calls.extend(summary['calls'])
        check=call('check-document --final',lambda:store.check_document(final=True))
        summary.update(actual_pages=len(check['pages']),deterministic_passed=check['passed'],unresolved=check['repair_targets'],repair_summary=store.metadata().get('repair_summary'))
        if not check['passed']:raise RuntimeError('Deterministic findings remain')
    host=dict(private_root=args.output/'host-private')
    if args.live:
        from platform_app.agent_core.config import ModelProfile
        from platform_app.agent_core.llm import build_chat_model
        key=getpass.getpass('DeepSeek visual test key (hidden): ')
        profile=ModelProfile(id='deepseek/'+args.model,model=args.model,api_key=key,base_url='https://api.deepseek.com/v1',api='chat_completions',input=('text','image'),max_retries=0)
        chat=build_chat_model(profile,streaming=False,trust_env=True,timeout=90);chat.max_tokens=2200
        host.update(vision=lambda:(profile.id,chat),vision_timeout=100)
    service=adapter.Documents(files,host=host)
    start=time.monotonic()
    if args.review_existing:service.reviews.request(store.path,store.metadata()['revision'])
    else:service.reviews.resume(store.path)
    summary['queue_return_ms']=round((time.monotonic()-start)*1000,3)
    print('visual queue started',summary['actual_pages'],flush=True)
    deadline=time.monotonic()+args.timeout;last=-1
    while time.monotonic()<deadline:
        state=store.metadata();count=len(state.get('aesthetic_reviews') or {})
        if count!=last:print('reviewed pages',count,flush=True);last=count
        if state.get('document_review'):break
        service.sync();time.sleep(.2)
    state=store.metadata();delivery=service.quality_delivery(state)
    summary.update(revision=state['revision'],design_id=state['selected_design']['id'],delivery=delivery,page_reviews=state.get('aesthetic_reviews'),document_review=state.get('document_review'),visual_duration_s=round(time.monotonic()-start,3),live_model=args.model if args.live else None)
    if delivery['deterministic']=='passed':summary['finalize']=call('finalize',lambda:store.finalize(state['revision']))
    atomics=sum(event.get('operation_count',0) for event in store.events() if event.get('section_id'))
    summary.update(calls=calls,atomic_operations=atomics,new_tool_calls=len(calls),legacy_protocol_calls=1+atomics+(atomics+2)//3+2,editable=True)
    summary['call_reduction']=round(1-summary['new_tool_calls']/summary['legacy_protocol_calls'],4)
    from docx import Document
    Document(store.path);assert adapter.engine.o.validate_parts(adapter.engine.o.read_parts(store.path))['ok']
    (args.output/'acceptance.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2)+'\n');service.close()
    print(json.dumps({k:summary[k] for k in ['actual_pages','revision','delivery','call_reduction']},ensure_ascii=False),flush=True)

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--output',type=Path,required=True);p.add_argument('--live',action='store_true');p.add_argument('--review-existing',action='store_true');p.add_argument('--model',default='deepseek-flash');p.add_argument('--sections',type=int,default=6);p.add_argument('--paragraphs',type=int,default=8);p.add_argument('--timeout',type=int,default=900);run(p.parse_args())
