"""Read-only PPTX indexing, preview, visual-review audit and issue dismissal HTTP API.

Visual review is done by the main Agent through ``submit-review``; the host
never calls a model. It keeps a private record of every submitted review and
only trusts finalized verdicts that appear in that record.
"""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import importlib.util
import io
import json
import logging
from pathlib import Path
import sqlite3
import tempfile
import threading
import subprocess
import zipfile
from typing import Literal
from fastapi import APIRouter,HTTPException
from fastapi.responses import Response,FileResponse
from pydantic import BaseModel,Field
from platform_app.artifact_runtime import validate_embedded_resources
from platform_app.office_review import BackgroundReviews, ReviewLedger

spec=importlib.util.spec_from_file_location('pptx_feature_engine',Path(__file__).parent/'scripts'/'office_pptx.py')
engine=importlib.util.module_from_spec(spec); spec.loader.exec_module(engine)
PresentationStore=engine.PresentationStore
LOG=logging.getLogger(__name__)


class ReviewCoordinator(BackgroundReviews):
    """Records submitted main-Agent visual reviews and verifies finalized verdicts against that record."""
    def __init__(self,service,host):
        self.service=service;self.host=host or {}
        private=self.host.get('private_root')
        self.private_root=Path(private) if private else Path(service.temporary_root or tempfile.gettempdir())/'pptx-host-review'
        self.private_root.mkdir(parents=True,exist_ok=True,mode=0o700)
        self.ledger=ReviewLedger(self.private_root/'vision-reviews.sqlite')
        super().__init__(service, self.host)
    def store(self,path):
        return PresentationStore(path,temporary_root=self.private_root/'renders')
    def observe(self,path,event):
        kind=event.get('type')
        if kind=='presentation_aesthetic_review':
            self.audit(path,event.get('presentation_id'),event.get('slide_id'),(event.get('review') or {}).get('aesthetic_review'),'slide')
        elif kind=='presentation_deck_review':
            self.audit(path,event.get('presentation_id'),None,event.get('deck_review'),'deck')
        elif kind=='presentation_finalized':
            self.schedule(('verify',str(path),event.get('revision')),self.verify_finalized,path,event)
    def resume(self,path):
        """Reviews are recorded from the event journal only; nothing is pending on the host."""
    def audit(self,path,presentation_id,slide_id,review,kind):
        review=review or {}
        identity=review.get('review_id')
        if not identity or review.get('reviewer')!='main_agent' or self.ledger.get(identity):return
        try:
            self.ledger.record(id=identity,kind=kind,presentation_id=presentation_id,path=str(path),slide_id=slide_id,revision=review.get('revision'),
                render_sha256=review.get('render_sha256'),pixel_sha256=review.get('pixel_sha256'),model_id=review.get('reviewer'),
                prompt_version=review.get('prompt_version'),status=review.get('status'),summary=review.get('summary'),issues=review.get('issues'),
                checks=review.get('checks'),flags=review.get('flags'),error=json.dumps(review.get('error')) if review.get('error') else None,applied=1)
        except sqlite3.IntegrityError:pass
    def verify_finalized(self,path,event):
        """Finalization written by the sandbox is only trusted for verdicts that went through submit-review."""
        with self.store(path).locked() as(c,state):identity=(state or {}).get('presentation_id')
        problems=[]
        # Visual review never gates delivery; this only proves that claimed verdicts were really submitted.
        for sid,claimed in (event.get('aesthetics') or {}).items():
            if claimed.get('status') not in ('passed','failed','uncertain'):continue
            record=self.ledger.get(claimed.get('review_id')) if claimed.get('review_id') else None
            if not record or record['slide_id']!=sid or record['presentation_id']!=identity or record['status']!=claimed['status']:
                problems.append(f'{sid}: claimed visual verdict {claimed.get("status")} is not on record')
        self.service.emit(dict(type='presentation_finalize_verification',presentation_id=identity,revision=event.get('revision'),
            path=Path(path).relative_to(self.service.root).as_posix(),finalize_verified=not problems,verification_problems=problems))


class Presentations:
    def __init__(self,root,emit,temporary_root=None,host=None):
        self.root=Path(root).resolve(); self.temporary_root=temporary_root; self.emit=emit; self.cursors={}; self.bound_paths={}; self.lock=threading.RLock()
        self.reviews=ReviewCoordinator(self,host)
        self.preview_executor=ThreadPoolExecutor(max_workers=1,thread_name_prefix='pptx-preview')
        self.preview_lock=threading.Lock();self.preview_pending={};self.preview_running=set();self.closed=False
    def store(self, path):
        return PresentationStore(path, temporary_root=self.temporary_root)
    def bind_state(self,record):
        self.bound_paths={identity:item['path'] for identity,item in record.get('presentations',{}).items()}
        self.cursors=dict(record.get('artifact_cursors',{}).get('pptx',{}))
        for path in self.paths():
            if path.relative_to(self.root).as_posix() not in self.cursors and path.relative_to(self.root).as_posix() not in self.bound_paths.values():
                if (path.parent/'.pptx-state'/path.name/'history.sqlite').exists():
                    events=self.store(path).events()
                    self.cursors[path.relative_to(self.root).as_posix()]=events[-1]['store_seq'] if events else 0
        for path in self.paths():
            if (path.parent/'.pptx-state'/path.name/'history.sqlite').exists():self.reviews.resume(path)
    def paths(self):
        return [p for p in self.root.rglob('*.pptx') if not p.is_symlink() and '.pptx-state' not in p.relative_to(self.root).parts and p.resolve().is_relative_to(self.root.resolve())]
    def presentation_path(self,identity):
        if identity not in self.bound_paths:raise ValueError('Unknown presentation')
        path=self.root/self.bound_paths[identity]
        if path.is_symlink() or not path.resolve().is_relative_to(self.root.resolve()):raise ValueError('Invalid presentation path')
        return path
    def close(self):
        self.closed=True;self.preview_executor.shutdown(wait=False,cancel_futures=True);self.reviews.close()
    def schedule_preview(self,path,event):
        if not (event.get('manifest') or {}).get('slides'):return
        path=Path(path)
        with self.preview_lock:
            if self.closed:return
            self.preview_pending[path]=event['revision']
            if path in self.preview_running:return
            self.preview_running.add(path)
        self.preview_executor.submit(self._preview_loop,path)
    def _preview_loop(self,path):
        while not self.closed:
            threading.Event().wait(.2)  # Coalesce rapid saves, not the Agent's whole run.
            with self.preview_lock:
                target=self.preview_pending.pop(path,None)
                if target is None:
                    self.preview_running.discard(path);return
            store=self.store(path)
            try:
                if store.status()['revision']!=target:continue
                store.preview()
            except (OSError,RuntimeError,ValueError,subprocess.TimeoutExpired) as exc:
                with store.locked() as(c,state):
                    if state and state['revision']==target:
                        store.review_event(c,state,'presentation_preview_error',preview_error=type(exc).__name__+': '+str(exc)[:200])
                LOG.warning('PPTX preview failed: revision=%s exception=%s',target,type(exc).__name__)
            finally:
                if not self.closed:
                    self.sync()
                    kept=store.retain_recent_history()
                    self.reviews.store(path).prune_render_cache(kept)
        with self.preview_lock:self.preview_running.discard(path)
    def sync(self):
        with self.lock:
            for path in self.paths():
                if path.is_symlink() or not (path.parent/'.pptx-state'/path.name/'history.sqlite').exists():continue
                for event in self.store(path).events(self.cursors.get(path.relative_to(self.root).as_posix(),0)):
                    event['path']=path.relative_to(self.root).as_posix()
                    identity=event.get('presentation_id')
                    if identity in self.bound_paths and self.bound_paths[identity]!=event['path']:
                        self.cursors[event['path']]=event['store_seq']
                        continue
                    if identity:self.bound_paths[identity]=event['path']
                    self.emit(event); self.cursors[path.relative_to(self.root).as_posix()]=event['store_seq']
                    self.reviews.observe(path,event)
                    if event.get('type') in ('presentation_initialized','presentation_revision','presentation_restored'):
                        self.schedule_preview(path,event)
    def detect_external(self):
        # Every complete external save becomes a version; never publish over its writer.
        for path in self.paths():
            if path.is_symlink():continue
            store=self.store(path)
            relative=path.relative_to(self.root).as_posix()
            try:
                with store.locked() as(c,state):
                    identity=state['presentation_id'] if state else None
                if identity is None:
                    try: identity = engine.identifier(path.stem) if len(Path(relative).parts) == 1 else 'external-' + hashlib.sha256(relative.encode()).hexdigest()[:20]
                    except ValueError: identity = 'external-' + hashlib.sha256(relative.encode()).hexdigest()[:20]
                    if identity in self.bound_paths and self.bound_paths[identity] != relative:
                        identity = 'external-' + hashlib.sha256(relative.encode()).hexdigest()[:20]
                store.track_external(identity)
                kept=store.retain_recent_history()
                self.reviews.store(path).prune_render_cache(kept)
            except (ValueError,OSError,zipfile.BadZipFile):
                # An invalid/partially-written ZIP never displaces the last good revision.
                continue
        self.sync()
    def feedback(self,text,context):
        identity=context.get('presentation_id') or context.get('id'); sid=context.get('slide_id'); revision=context.get('revision')
        state=self.store(self.presentation_path(identity)).status()
        if type(revision)is not int or revision>state['revision'] or sid not in [s['slide_id'] for s in state['manifest']['slides']]:raise ValueError('Invalid presentation/slide feedback version')
        return text+f'\n[Presentation feedback: presentation_id={identity}, slide_id={sid}, viewed_revision={revision}, current_revision={state["revision"]}. Prioritize this slide, invalidate affected checks, recheck before continuing.]'
    def dismiss_issues(self,identity,revision,issue_ids,notes='',slide_id=None):
        """Record issue dismissals without accepting/rejecting the model review."""
        store=self.store(self.presentation_path(identity))
        with store.locked() as(c,state):
            target=(state.get('reviews',{}).get(slide_id) or {}).get('aesthetic_review') if slide_id else state.get('deck_review')
        decision_id=self.reviews.ledger.decide(review_id=(target or {}).get('review_id'),presentation_id=identity,slide_id=slide_id,
            revision=revision,decision='dismiss_issues',issue_ids=list(issue_ids),notes=notes,actor='human')
        result=store.dismiss_issues(revision,issue_ids,decision_id,notes,slide_id)
        self.sync();return result

def create_service(root,emit,temporary_root=None,host=None):return Presentations(root,emit,temporary_root=temporary_root,host=host)


def create_router(host):
    router=APIRouter(prefix='/api/agent/sessions')
    def store_for(session_id,presentation_id):
        service=host.service(session_id,'pptx'); record=host.session(session_id)
        if presentation_id not in record.get('presentations',{}):raise HTTPException(404,'Presentation does not belong to this session')
        try:return service,service.store(service.presentation_path(presentation_id))
        except ValueError:raise HTTPException(422,'Invalid presentation ID')
    @router.get('/{session_id}/presentations')
    def presentations(session_id:str):
        service=host.service(session_id,'pptx'); service.detect_external(); record=host.session(session_id); result=[]
        for identity in record.get('presentations',{}):
            try:
                path=service.presentation_path(identity)
                if not path.is_file():continue
                result.append({**service.store(path).status(),'path':record['presentations'][identity]['path'],
                **{key:record['presentations'][identity][key] for key in ('finalize_verified','verification_problems') if key in record['presentations'][identity]}})
            except (ValueError,OSError):continue
        return result
    @router.post('/{session_id}/presentations/{presentation_id}/preview')
    def preview(session_id:str,presentation_id:str):
        service,store=store_for(session_id,presentation_id)
        service.detect_external()
        try:
            validate_embedded_resources(store.path)
            result=store.preview()
        except zipfile.BadZipFile as exc:
            raise HTTPException(409,'PPT 尚未写入完成或不是完整的 PPTX 文件，请稍后重试。') from exc
        except ValueError as exc:
            if str(exc).startswith('External modification'):
                raise HTTPException(409,'PPT 文件已在版本系统外被修改，当前文件与已登记版本不一致；请先登记新版本再预览。') from exc
            if str(exc)=='Revision conflict':
                raise HTTPException(409,'PPT 在生成预览期间更新了版本，请重试预览。') from exc
            raise HTTPException(409,'演示文稿预览失败，文件或渲染结果无效，请查看服务端日志。') from exc
        except (OSError,RuntimeError) as exc:raise HTTPException(409,'演示文稿预览暂不可用，请检查 LibreOffice') from exc
        service.sync()
        return {**result, 'path': store.path.relative_to(service.root).as_posix()}
    @router.get('/{session_id}/presentations/{presentation_id}/revisions/{revision}')
    def snapshot(session_id:str,presentation_id:str,revision:int):
        _,store=store_for(session_id,presentation_id)
        try:data=store.snapshot(revision)
        except ValueError:raise HTTPException(404,'Unknown revision')
        return Response(data,media_type='application/vnd.openxmlformats-officedocument.presentationml.presentation',headers={'Content-Disposition':f'attachment; filename="presentation-r{revision}.pptx"','Cache-Control':'private, max-age=31536000, immutable'})
    @router.get('/{session_id}/presentations/{presentation_id}/renders/{revision}/{filename}')
    def rendered(session_id:str,presentation_id:str,revision:int,filename:str):
        import re
        _,store=store_for(session_id,presentation_id)
        if revision<0 or not re.fullmatch(r'slide-\d{3}\.png',filename):raise HTTPException(404,'Unknown rendered page')
        path=store.render_directory(revision)/filename
        if not path.is_file():raise HTTPException(404,'Render unavailable')
        return FileResponse(path,headers={'Cache-Control':'private, max-age=31536000, immutable'})
    @router.get('/{session_id}/presentations/{presentation_id}/assets/{revision}/{slide_id}/{element_id}')
    def asset(session_id:str,presentation_id:str,revision:int,slide_id:str,element_id:str):
        _,store=store_for(session_id,presentation_id)
        try:
            prs=engine.Presentation(io.BytesIO(store.snapshot(revision))); shape=engine.find_element(engine.find_slide(prs,slide_id),element_id)
            return Response(shape.image.blob,media_type=shape.image.content_type,headers={'Cache-Control':'private, max-age=31536000, immutable'})
        except (ValueError,AttributeError):raise HTTPException(404,'Image unavailable')
    class AestheticDecision(BaseModel):
        model_config={'extra':'forbid'}
        slide_id:str|None=None
        revision:int=Field(ge=0)
        decision:Literal['dismiss_issues']
        issue_ids:list[str]=Field(default_factory=list,max_length=12)
        notes:str=Field(default='',max_length=2000)
    @router.post('/{session_id}/presentations/{presentation_id}/aesthetic-decision')
    def aesthetic_decision(session_id:str,presentation_id:str,value:AestheticDecision):
        service,store=store_for(session_id,presentation_id)
        try:result=service.dismiss_issues(presentation_id,value.revision,value.issue_ids,value.notes,value.slide_id)
        except ValueError as exc:raise HTTPException(409,str(exc))
        return {**result,'path':store.path.relative_to(service.root).as_posix()}
    return router
