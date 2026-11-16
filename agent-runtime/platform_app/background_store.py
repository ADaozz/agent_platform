"""Minimal SQLite persistence for background subagent runs (no thread restore)."""
from __future__ import annotations

import logging

from platform_app.agent_core.subagents.log_store import redact_known_secrets

from . import domain as d

KIND = 'background_task'
ACTIVE = frozenset({'running'})
DESCRIPTION_LIMIT = 200
RESULT_LIMIT = 200
LOG = logging.getLogger(__name__)
_SAFE_STATUS = {
    'failed': '后台任务失败',
    'cancelled': '后台任务已取消',
    'interrupted': '后台任务已中断，不会自动重执行',
}


def redact_secrets(value: str | None, secrets: tuple[str, ...] = ()) -> str:
    """Use the subagent log store's known-secret replacement."""
    return redact_known_secrets(str(value or ''), tuple(secrets or ()))


def _brief(value: str | None, limit: int = DESCRIPTION_LIMIT, secrets: tuple[str, ...] = ()) -> str:
    text = ' '.join(redact_secrets(value, secrets).split())
    return text[:limit]


def upsert(task: dict, secrets: tuple[str, ...] = ()) -> dict:
    record = {
        'id': task['run_id'],
        'run_id': task['run_id'],
        'session_id': task['session_id'],
        'tool_call_id': task.get('tool_call_id') or '',
        'description': _brief(task.get('description'), DESCRIPTION_LIMIT, secrets),
        'status': task['status'],
        'created_at': task.get('created_at'),
        'finished_at': task.get('finished_at'),
        'result': safe_result(task.get('status'), task.get('result'), secrets),
    }
    return d.put(KIND, record)


def safe_result(status: str | None, result: str | None, secrets: tuple[str, ...] = ()) -> str:
    """Failures keep a category, not the raw exception or model output."""
    if status in _SAFE_STATUS:
        return _SAFE_STATUS[status]
    return _brief(result, RESULT_LIMIT, secrets)


def mark_started(*, run_id: str, session_id: str, tool_call_id: str, description: str, created_at: str,
                 secrets: tuple[str, ...] = ()) -> dict:
    return upsert({
        'run_id': run_id,
        'session_id': session_id,
        'tool_call_id': tool_call_id,
        'description': description,
        'status': 'running',
        'created_at': created_at,
        'finished_at': None,
        'result': '',
    }, secrets)


def mark_finished(*, run_id: str, session_id: str, status: str, result: str, finished_at: str,
                  tool_call_id: str = '', description: str = '', created_at: str | None = None,
                  secrets: tuple[str, ...] = ()) -> dict:
    previous = get(run_id) or {}
    return upsert({
        'run_id': run_id,
        'session_id': session_id,
        'tool_call_id': tool_call_id or previous.get('tool_call_id') or '',
        'description': description or previous.get('description') or '',
        'status': status,
        'created_at': created_at or previous.get('created_at'),
        'finished_at': finished_at,
        'result': result,
    }, secrets)


def get(run_id: str) -> dict | None:
    try:
        return d.get(KIND, run_id)
    except KeyError:
        return None


def for_session(session_id: str) -> list[dict]:
    return [item for item in d.all_records(KIND) if item.get('session_id') == session_id]


def running_for_session(session_id: str) -> list[dict]:
    return [item for item in for_session(session_id) if item.get('status') in ACTIVE]


def interrupt_unfinished() -> int:
    """On process start: keep completed results; mark unfinished runs interrupted."""
    changed = 0
    for item in d.all_records(KIND):
        if item.get('status') in ACTIVE:
            item['status'] = 'interrupted'
            item['finished_at'] = item.get('finished_at') or item.get('created_at')
            item['result'] = item.get('result') or '服务重启，后台任务已中断且不会自动重执行。'
            d.put(KIND, item)
            changed += 1
    return changed


def public_task(item: dict) -> dict:
    return {
        'run_id': item.get('run_id') or item.get('id'),
        'tool_call_id': item.get('tool_call_id') or '',
        'status': item.get('status') or 'interrupted',
        'description': item.get('description') or '',
        'created_at': item.get('created_at'),
        'finished_at': item.get('finished_at'),
        'result': item.get('result') or '',
    }
