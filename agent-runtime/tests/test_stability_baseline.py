"""基线回归：记录 main 上已有、修复期间不得破坏的行为。"""
import pytest
from fastapi.testclient import TestClient

from platform_app import domain as d, models as m, runtime as rt
from platform_app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DATA', tmp_path)
    d.init()
    rt.RUNTIMES.clear()
    m.save({'default': 'test/model', 'timeout': 60, 'models': {
        'test': {'base_url': 'https://example.com/v1', 'api_key': 'sk-baseline', 'api': 'chat_completions',
                 'models': {'model': {}}}
    }}, 0)
    yield TestClient(app)
    rt.RUNTIMES.clear()


def test_initialize_marks_active_sessions_interrupted(client):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    record = d.get('session', session_id)
    record['status'] = 'running'
    d.put('session', record)
    rt.initialize()
    restored = d.get('session', session_id)
    assert restored['status'] == 'interrupted'
    assert '服务重启' in (restored.get('error') or '')


def test_delete_running_main_session_returns_409(client):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    record = d.get('session', session_id)
    record['status'] = 'running'
    d.put('session', record)
    assert client.delete(f'/api/agent/sessions/{session_id}').status_code == 409
    assert client.get(f'/api/agent/sessions/{session_id}').status_code == 200


def test_personal_model_rejects_non_http_schemes(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DATA', tmp_path)
    d.init()
    with pytest.raises(ValueError, match='base_url'):
        m.save_personal('1001', {
            'default': 'mine/chat',
            'models': {'mine': {'base_url': 'file:///etc/passwd', 'api_key': 'sk-x',
                                'api': 'chat_completions', 'models': {'chat': {}}}},
        }, 0)


def test_recovery_context_text_covers_pending_aborted_error():
    from platform_app.agent_core.middleware.recovery import RecoveryContext
    from platform_app.agent_core.session import StopReason
    for reason in (StopReason.PENDING, StopReason.ABORTED, StopReason.ERROR):
        ctx = RecoveryContext.for_stop_reason(reason)
        assert ctx is not None and ctx.text
        assert '检查' in ctx.text
        assert ctx.armed is False


def test_waiting_confirmation_survives_initialize(client):
    session_id = client.post('/api/agent/sessions', json={'model_id': 'test/model'}).json()['id']
    record = d.get('session', session_id)
    record['status'] = 'waiting_confirmation'
    record['pending_tool_calls'] = [{'toolCallId': 't1', 'name': 'execute'}]
    d.put('session', record)
    rt.initialize()
    assert d.get('session', session_id)['status'] == 'waiting_confirmation'
