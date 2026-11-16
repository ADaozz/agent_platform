"""Process-level recovery: simulate runtime restart without replaying tools."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

pytest.importorskip('httpx')


ROOT = Path(__file__).resolve().parents[1]


def _wait_http(url: str, timeout: float = 30.0):
    import httpx
    deadline = time.monotonic() + timeout
    last = None
    while time.monotonic() < deadline:
        try:
            response = httpx.get(url, timeout=1.0)
            if response.status_code < 500:
                return response
            last = response.status_code
        except Exception as exc:  # noqa: BLE001
            last = exc
        time.sleep(0.1)
    raise AssertionError(f'service did not become ready: {last}')


def _run_worker(mode, data):
    import subprocess
    env = os.environ.copy()
    env['PLATFORM_DATA_DIR'] = str(data)
    env['PYTHONPATH'] = str(ROOT)
    python = ROOT / '.venv' / 'bin' / 'python'
    if not python.exists():
        python = Path(sys.executable)
    return subprocess.run(
        [str(python), str(ROOT / 'tests' / 'crash_recovery_worker.py'), mode, str(data)],
        cwd=str(ROOT), env=env, capture_output=True, text=True, timeout=90,
    )


@pytest.mark.integration
def test_kill_after_file_write_does_not_replay_tool(tmp_path):
    data = tmp_path / 'crash-write'
    data.mkdir()
    crashed = _run_worker('write-kill', data)
    assert crashed.returncode in (-9, 137), (crashed.returncode, crashed.stdout, crashed.stderr)
    continued = _run_worker('continue', data)
    assert continued.returncode == 0, continued.stderr
    body = json.loads(continued.stdout.strip().splitlines()[-1])
    assert body['marker'] == 'x'
    assert '不要重写标记文件' in body['output']


@pytest.mark.integration
def test_kill_while_waiting_for_approval_keeps_interrupt(tmp_path):
    data = tmp_path / 'crash-approval'
    data.mkdir()
    crashed = _run_worker('approval-kill', data)
    assert crashed.returncode != 0, crashed.stderr
    inspected = _run_worker('inspect', data)
    assert inspected.returncode == 0, inspected.stderr
    body = json.loads(inspected.stdout.strip().splitlines()[-1])
    assert body['status'] == 'waiting_confirmation'
    assert body['pending']


@pytest.mark.integration
def test_uvicorn_restart_preserves_checkpoint_and_marks_interrupted(tmp_path):
    """Spawn a real uvicorn, mark a session running, kill the process, restart, assert recovery surface."""
    data = tmp_path / 'platform-data'
    data.mkdir()
    env = os.environ.copy()
    env['PLATFORM_DATA_DIR'] = str(data)
    env['PYTHONPATH'] = str(ROOT)
    python = str(ROOT / '.venv' / 'bin' / 'python')
    if not Path(python).exists():
        python = sys.executable

    def start():
        return subprocess.Popen(
            [python, '-m', 'uvicorn', 'platform_app.main:app', '--host', '127.0.0.1', '--port', '8765'],
            cwd=str(ROOT),
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
        )

    import httpx
    proc = start()
    try:
        _wait_http('http://127.0.0.1:8765/api/status')
        with httpx.Client(base_url='http://127.0.0.1:8765', timeout=30.0) as client:
            put = client.put('/api/models', json={
                'llm': {
                    'default': 'test/model', 'timeout': 60,
                    'models': {'test': {
                        'base_url': 'https://example.com/v1', 'api_key': 'sk-integration',
                        'api': 'chat_completions', 'models': {'model': {}},
                    }},
                },
                'revision': 0,
            })
            assert put.status_code == 200, put.text
            session = client.post('/api/agent/sessions', json={'model_id': 'test/model'})
            assert session.status_code == 201, session.text
            session_id = session.json()['id']

        # Simulate an unclean exit while the platform row still says running.
        # Direct SQLite edit mirrors a crash before initialize() can settle the row.
        import sqlite3, json
        db = data / 'platform.sqlite'
        connection = sqlite3.connect(db)
        row = connection.execute('SELECT data FROM records WHERE kind=? AND id=?', ('session', session_id)).fetchone()
        record = json.loads(row[0])
        record['status'] = 'running'
        connection.execute(
            'UPDATE records SET data=? WHERE kind=? AND id=?',
            (json.dumps(record, ensure_ascii=False), 'session', session_id),
        )
        connection.commit()
        connection.close()

        proc.kill()
        proc.wait(timeout=10)

        proc = start()
        _wait_http('http://127.0.0.1:8765/api/status')
        with httpx.Client(base_url='http://127.0.0.1:8765', timeout=30.0) as client:
            restored = client.get(f'/api/agent/sessions/{session_id}')
            assert restored.status_code == 200, restored.text
            body = restored.json()
            assert body['status'] == 'interrupted'
            assert '服务重启' in (body.get('error') or '')
    finally:
        if proc.poll() is None:
            proc.kill()
            proc.wait(timeout=10)
        if proc.stdout:
            out = proc.stdout.read()
            if out and os.environ.get('VERBOSE_RECOVERY') == '1':
                sys.stderr.write(out.decode('utf-8', errors='replace'))
