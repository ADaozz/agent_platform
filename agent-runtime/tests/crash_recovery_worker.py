"""Child process for crash-recovery checks. SIGKILL avoids a clean shutdown."""
import json
import os
import shlex
import signal
import sys
from pathlib import Path

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from fastapi.testclient import TestClient


TARGET = {'path': 'marker.txt'}


def main():
    mode, data = sys.argv[1], sys.argv[2]
    os.environ['PLATFORM_DATA_DIR'] = data
    from platform_app import domain as d, models as m
    from platform_app.main import app
    from platform_app.workspace import resolve

    class Model(BaseChatModel):
        @property
        def _llm_type(self):
            return 'crash-worker'

        def bind_tools(self, tools, **kwargs):
            return self

        def _generate(self, messages, stop=None, run_manager=None, **kwargs):
            user = next((item.content for item in reversed(messages) if item.type == 'human'), '')
            if mode == 'write-kill' and not any(isinstance(item, ToolMessage) for item in messages):
                command = 'printf x >> ' + shlex.quote(TARGET['path'])
                return ChatResult(generations=[ChatGeneration(message=AIMessage(
                    content='',
                    tool_calls=[{'name': 'execute', 'args': {'command': command}, 'id': 'w1', 'type': 'tool_call'}],
                ))])
            if mode == 'write-kill':
                os.kill(os.getpid(), signal.SIGKILL)
            if mode == 'approval-kill':
                return ChatResult(generations=[ChatGeneration(message=AIMessage(
                    content='',
                    tool_calls=[{'name': 'execute', 'args': {'command': 'printf should-not-run'}, 'id': 'e1', 'type': 'tool_call'}],
                ))])
            return ChatResult(generations=[ChatGeneration(message=AIMessage(content='continued-without-replay:' + str(user)))])

    def build_model(profile, **kwargs):
        model = Model()
        object.__setattr__(model, '_deep_agent_model_id', profile.id)
        return model

    import platform_app.agent_core.llm as llm
    import platform_app.agent_core.runner as runner_mod
    import platform_app.runtime as rt
    llm.build_chat_model = build_model
    runner_mod.build_chat_model = build_model
    rt.POOL.submit = lambda fn, *args: fn(*args)

    client = TestClient(app)
    if mode == 'inspect':
        sessions = client.get('/api/agent/sessions').json()
        session_id = sessions[0]['id']
        body = client.get(f'/api/agent/sessions/{session_id}').json()
        marker = list(Path(data).rglob('marker.txt'))
        print(json.dumps({
            'status': body['status'],
            'output': body.get('output'),
            'pending': body.get('pending_tool_calls'),
            'background': body.get('background_tasks'),
            'marker': marker[0].read_text() if marker else None,
            'error': body.get('error'),
        }, ensure_ascii=False))
        return
    if mode == 'continue':
        sessions = client.get('/api/agent/sessions').json()
        session_id = sessions[0]['id']
        assert client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': '不要重写标记文件'}).status_code == 202
        body = client.get(f'/api/agent/sessions/{session_id}').json()
        marker = list(Path(data).rglob('marker.txt'))
        print(json.dumps({'status': body['status'], 'output': body.get('output'), 'marker': marker[0].read_text() if marker else None}, ensure_ascii=False))
        return

    d.init()
    m.save({'default': 'test/model', 'timeout': 60, 'models': {'test': {
        'base_url': 'https://example.com/v1', 'api_key': 'sk-crash', 'api': 'chat_completions', 'models': {'model': {}},
    }}}, 0)
    payload = {'model_id': 'test/model'}
    if mode == 'write-kill':
        payload.update(permission_mode='allow', permission_confirmation='ALLOW')
    created = client.post('/api/agent/sessions', json=payload)
    if created.status_code != 201:
        print(created.text, file=sys.stderr)
        sys.exit(2)
    session_id = created.json()['id']
    if mode == 'write-kill':
        TARGET['path'] = str(resolve(session_id).files_root / 'marker.txt')
    response = client.post(f'/api/agent/sessions/{session_id}/messages', json={'text': 'write the marker' if mode == 'write-kill' else 'needs approval'})
    if mode == 'approval-kill':
        body = client.get(f'/api/agent/sessions/{session_id}').json()
        if body['status'] != 'waiting_confirmation':
            print(json.dumps({'error': 'not-waiting', 'status': body['status'], 'detail': response.text}), file=sys.stderr)
            sys.exit(2)
        os.kill(os.getpid(), signal.SIGKILL)
    print(response.status_code)


if __name__ == '__main__':
    main()
