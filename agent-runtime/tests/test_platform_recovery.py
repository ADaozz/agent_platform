"""Platform Runtime.build 必须走 deep_agent_cli 同等的 switch_session 恢复路径。"""
import json

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


def test_background_result_redacts_secrets_and_hides_failures():
    from platform_app import background_store as bg
    secret = 'vendor-token-not-a-prefix'
    assert secret not in bg.redact_secrets(f'token {secret} tail', secrets=(secret,))
    session_id = 's'
    bg.mark_started(run_id='r1', session_id=session_id, tool_call_id='t', description=f'use {secret}', created_at='t0', secrets=(secret,))
    assert secret not in bg.get('r1')['description']
    bg.mark_finished(run_id='r1', session_id=session_id, status='failed', result=f'boom {secret}', finished_at='t1', secrets=(secret,))
    assert bg.get('r1')['result'] == '后台任务失败'
    assert secret not in json.dumps(bg.get('r1'))


def test_delete_keeps_store_when_runner_close_times_out(client):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'hello'}).status_code == 202
    runtime = rt.RUNTIMES[session_id]
    store = runtime.runner.session_store
    checkpoint = store.path

    def timeout_close():
        raise RuntimeError('model stream still open')

    runtime.runner.close = timeout_close
    response = client.delete(f'/api/agent/sessions/{session_id}')
    assert response.status_code == 409
    assert not store._closed
    assert checkpoint.is_file()
    assert client.get(f'/api/agent/sessions/{session_id}').status_code == 200


def test_failed_build_retries_close_before_creating_a_new_runner(client):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'hello'}).status_code == 202
    runtime = rt.RUNTIMES[session_id]
    runner = runtime.runner
    real_close = runner.close
    attempts = {'n': 0}

    def flaky_close():
        attempts['n'] += 1
        runner._closed = True
        if attempts['n'] == 1:
            raise RuntimeError('model stream still open')
        return real_close()

    runner.close = flaky_close
    runtime.release_partial_runner(runner, runner.session_store, None)
    assert runtime.runner is None
    assert runtime._pending_cleanup is runner
    rebuilt = runtime.build()
    assert attempts['n'] == 2
    assert rebuilt is not runner
    assert runtime._pending_cleanup is None
    assert not getattr(rebuilt, '_closed', False)
    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'continue after cleanup'}).status_code == 202
    assert client.get(f'/api/agent/sessions/{session_id}').json()['output'] == 'ok'


def test_schedule_does_not_record_message_while_cleanup_still_times_out(client):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'hello'}).status_code == 202
    runtime = rt.RUNTIMES[session_id]
    runner = runtime.runner
    real_close = runner.close
    before = list(d.get('session', session_id)['messages'])

    def still_timing_out():
        runner._closed = True
        raise RuntimeError('model stream still open')

    runner.close = still_timing_out
    runtime.release_partial_runner(runner, runner.session_store, None)
    rejected = client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'not accepted'})
    assert rejected.status_code == 409
    assert d.get('session', session_id)['messages'] == before

    runner.close = real_close
    accepted = client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'accepted after cleanup'})
    assert accepted.status_code == 202
    recorded = [item['content'] for item in client.get(f'/api/agent/sessions/{session_id}').json()['messages']]
    transcript = [block.content for block in runtime.runner.load_session(session_id).transcript if block.kind == 'user']
    assert recorded == ['hello', 'accepted after cleanup']
    assert transcript == recorded


def test_build_checkpoint_read_failure_does_not_delete_workspace(client, monkeypatch):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'hello'}).status_code == 202
    runtime = rt.RUNTIMES[session_id]
    runtime.runner.close()
    runtime.runner.session_store.close()
    runtime.runner = None
    checkpoint = resolve(session_id).session_root / 'checkpoint.sqlite'
    assert checkpoint.is_file()

    def fail_switch(self, session):
        raise RuntimeError('checkpoint read failed')

    monkeypatch.setattr('platform_app.agent_core.runner.AgentRunner.switch_session', fail_switch)
    with pytest.raises(RuntimeError, match='checkpoint read failed'):
        rt.runtime(session_id).build()
    assert checkpoint.is_file()
    assert resolve(session_id).files_root.exists()
