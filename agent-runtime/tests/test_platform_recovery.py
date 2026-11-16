"""Platform Runtime.build 必须走 deep_agent_cli 同等的 switch_session 恢复路径。"""
import ipaddress

import pytest
from fastapi.testclient import TestClient
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from platform_app import domain as d, models as m, runtime as rt
from platform_app.agent_core.middleware.recovery import RecoveryContext, RecoveryContextMiddleware, reset_recovery_context, set_recovery_context
from platform_app.agent_core.session import SessionStore, StopReason
from platform_app.main import app
from platform_app.workspace import resolve


class ScriptedModel(BaseChatModel):
    replies: list

    @property
    def _llm_type(self):
        return 'platform-recovery'

    def bind_tools(self, tools, **kwargs):
        return self

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        if not self.replies:
            raise AssertionError('no scripted replies left')
        msg = self.replies.pop(0)
        return ChatResult(generations=[ChatGeneration(message=msg)])


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DATA', tmp_path)
    d.init()
    rt.RUNTIMES.clear()
    m.save({'default': 'test/model', 'timeout': 60, 'models': {
        'test': {'base_url': 'https://example.com/v1', 'api_key': 'sk-recovery', 'api': 'chat_completions',
                 'models': {'model': {}}}
    }}, 0)

    def build_model(profile, **kwargs):
        model = ScriptedModel(replies=[AIMessage(content='ok')])
        object.__setattr__(model, '_deep_agent_model_id', profile.id)
        return model

    monkeypatch.setattr('platform_app.agent_core.llm.build_chat_model', build_model)
    monkeypatch.setattr('platform_app.agent_core.runner.build_chat_model', build_model)
    monkeypatch.setattr(rt.POOL, 'submit', lambda fn, *args: fn(*args))
    yield TestClient(app)
    for runtime in list(rt.RUNTIMES.values()):
        if runtime.runner:
            try:
                runtime.runner.close()
                runtime.runner.session_store.close()
            except Exception:
                pass
    rt.RUNTIMES.clear()


def test_recovery_middleware_is_one_shot_and_keeps_user_text_raw():
    context = RecoveryContext.for_stop_reason(StopReason.ABORTED)
    assert context is not None
    context.armed = True
    original = SystemMessage(content='base')
    user = HumanMessage(content='真实用户输入')

    class Request:
        def __init__(self):
            self.system_message = original
            self.messages = [user]

        def override(self, **kwargs):
            clone = Request()
            clone.system_message = kwargs.get('system_message', self.system_message)
            clone.messages = self.messages
            return clone

    seen = []
    token = set_recovery_context(context)
    try:
        middleware = RecoveryContextMiddleware()
        middleware.wrap_model_call(Request(), lambda item: seen.append(item) or item)
        middleware.wrap_model_call(Request(), lambda item: seen.append(item) or item)
    finally:
        reset_recovery_context(token)
    assert '上一轮运行状态' in seen[0].system_message.content
    assert seen[1].system_message.content == 'base'
    assert context.text is None


def test_build_reloads_session_like_cli_switch_and_arms_recovery(client, monkeypatch):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'before'}).status_code == 202

    runtime = rt.RUNTIMES[session_id]
    store_path = resolve(session_id).session_root / 'checkpoint.sqlite'
    assert store_path.is_file()
    runtime.runner.session_store.touch(session_id, last_run_status=StopReason.ABORTED)
    runtime.runner.close()
    runtime.runner.session_store.close()
    runtime.runner = None
    rt.RUNTIMES.pop(session_id, None)

    record = d.get('session', session_id)
    record.update(status='interrupted', error='服务重启，本轮已中断；可发送新消息恢复会话。')
    d.put('session', record)

    monkeypatch.setattr('platform_app.agent_core.llm.build_chat_model',
                        lambda profile, **kwargs: ScriptedModel(replies=[AIMessage(content='recovered')]))
    monkeypatch.setattr('platform_app.agent_core.runner.build_chat_model',
                        lambda profile, **kwargs: ScriptedModel(replies=[AIMessage(content='recovered')]))

    rebuilt = rt.runtime(session_id).build()
    assert rebuilt._resume_context is not None
    assert '用户中止' in rebuilt._resume_context.text
    assert rebuilt._resume_context.armed is False
    # Checkpoint from the previous turn remains readable; no tool replay happens on rebuild alone.
    assert rebuilt.session_store.checkpointer.get_tuple(
        {'configurable': {'thread_id': session_id}}
    ) is not None

    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': '先检查，不要修改'}).status_code == 202
    assert client.get(f'/api/agent/sessions/{session_id}').json()['output'] == 'recovered'
    # One-shot: recovery context is cleared after the continued turn.
    assert rt.RUNTIMES[session_id].runner._resume_context is None
    transcript = rebuilt.load_session(session_id).transcript
    users = [block.content for block in transcript if block.kind == 'user']
    assert users == ['before', '先检查，不要修改']


def test_waiting_confirmation_keeps_interrupt_and_skips_recovery(client, monkeypatch):
    from platform_app.agent_core.run_events import InterruptKind
    from platform_app.agent_core.runner import SessionSnapshot
    from platform_app.agent_core.session import SessionInfo
    from datetime import datetime, timezone

    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    record = d.get('session', session_id)
    record.update(status='waiting_confirmation', pending_tool_calls=[{'toolCallId': 't1', 'name': 'execute'}])
    d.put('session', record)

    runtime = rt.Runtime(session_id)
    info = SessionInfo(
        id=session_id, title='x', created_at=datetime.now(timezone.utc), updated_at=datetime.now(timezone.utc),
        status='running', last_run_status=StopReason.DEFERRED,
    )
    snapshot = SessionSnapshot(
        info=info, transcript=[], interrupt_kind=InterruptKind.WAITING_CONFIRMATION,
        pending_tool_calls=[{'toolCallId': 't1', 'name': 'execute'}],
    )
    runtime.sync_checkpoint_interrupt(snapshot)
    synced = d.get('session', session_id)
    assert synced['status'] == 'waiting_confirmation'
    assert synced['pending_tool_calls'][0]['toolCallId'] == 't1'


def test_initialize_marks_background_running_interrupted(client):
    from platform_app import background_store as bg
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    bg.mark_started(run_id='abc123', session_id=session_id, tool_call_id='bg', description='work', created_at='2020-01-01T00:00:00+00:00')
    bg.mark_finished(run_id='done1', session_id=session_id, status='completed', result='ok',
                     finished_at='2020-01-01T00:01:00+00:00', tool_call_id='bg2', description='done',
                     created_at='2020-01-01T00:00:00+00:00')
    rt.initialize()
    running = bg.get('abc123')
    done = bg.get('done1')
    assert running['status'] == 'interrupted'
    assert done['status'] == 'completed' and done['result'] == 'ok'
    views = client.get(f'/api/agent/sessions/{session_id}').json()['background_tasks']
    assert {item['run_id']: item['status'] for item in views}['abc123'] == 'interrupted'


def test_delete_rejects_running_background_task(client):
    from platform_app import background_store as bg
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    bg.mark_started(run_id='alive1', session_id=session_id, tool_call_id='bg', description='work', created_at='2020-01-01T00:00:00+00:00')
    assert client.delete(f'/api/agent/sessions/{session_id}').status_code == 409
    assert client.get(f'/api/agent/sessions/{session_id}').status_code == 200
    bg.mark_finished(run_id='alive1', session_id=session_id, status='interrupted', result='stopped',
                     finished_at='2020-01-01T00:02:00+00:00')
    assert client.delete(f'/api/agent/sessions/{session_id}').status_code == 204
