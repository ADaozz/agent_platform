"""Aggregate model token usage from durable model_metrics journal events.

Usage events stream intermediate counts and may duplicate a completed call; model_metrics
is emitted once per generation. Cache-hit counts are taken from the paired usage event
immediately before each metrics snapshot.

Preset-model cost estimates (CNY / 1M tokens). DeepSeek uses peak/off-peak;
Qwen/GLM use flat rates (peak == off_peak). Estimates are not provider invoices.
"""
from __future__ import annotations

import json
from collections import defaultdict
from datetime import date, datetime, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from . import domain as d
from . import itam_bridge

_BJ = ZoneInfo('Asia/Shanghai')


def _flat(cache_hit: float, cache_miss: float, output: float) -> dict[str, dict[str, float]]:
    band = {'cache_hit': cache_hit, 'cache_miss': cache_miss, 'output': output}
    return {'off_peak': dict(band), 'peak': dict(band)}


# 元 / 百万 tokens — 仅收录设置页官方预设模型
# DeepSeek：空闲 = 高峰一半；高峰北京时间周一至周五 9–12、14–18（不含法定节假日）
# Qwen / GLM：无峰谷，peak 与 off_peak 相同
_MODEL_RATES: dict[str, dict[str, dict[str, float]]] = {
    'deepseek-flash': {
        'off_peak': {'cache_hit': 0.02, 'cache_miss': 1.0, 'output': 4.0},
        'peak': {'cache_hit': 0.04, 'cache_miss': 2.0, 'output': 8.0},
    },
    'deepseek-v4-pro': {
        'off_peak': {'cache_hit': 0.15, 'cache_miss': 4.5, 'output': 13.5},
        'peak': {'cache_hit': 0.30, 'cache_miss': 9.0, 'output': 27.0},
    },
    # 百炼：qwen3.8-flash / qwen3.7-plus(≤256K) / qwen4-max；隐式缓存命中价取官方或输入×20%
    'qwen3.8-flash': _flat(0.16, 0.8, 2.7),
    'qwen3.7-plus': _flat(0.4, 2.0, 8.0),
    'qwen4-max': _flat(0.5, 10.0, 30.0),
    # 智谱：官方刊例；flashx-legal 与 flashx 同价
    'glm-5.3': _flat(2.0, 8.0, 28.0),
    'glm-5.3-flash': _flat(0.23, 0.8, 2.8),
    'glm-5.3-flashx': _flat(0.57, 2.0, 7.0),
    'glm-5.3-flashx-legal': _flat(0.57, 2.0, 7.0),
}

# 未知模型兜底：按 DeepSeek Flash 空闲未命中 / 输出估算
_DEFAULT_RATES = {'cache_hit': 1.0, 'cache_miss': 1.0, 'output': 4.0}

# 中国法定节假日（放假日）；未收录年份仅按工作日峰谷估算
_PRC_HOLIDAYS: frozenset[date] = frozenset({
    # 2025
    date(2025, 1, 1), date(2025, 1, 28), date(2025, 1, 29), date(2025, 1, 30),
    date(2025, 1, 31), date(2025, 2, 1), date(2025, 2, 2), date(2025, 2, 3),
    date(2025, 2, 4), date(2025, 4, 4), date(2025, 4, 5), date(2025, 4, 6),
    date(2025, 5, 1), date(2025, 5, 2), date(2025, 5, 3), date(2025, 5, 4),
    date(2025, 5, 5), date(2025, 5, 31), date(2025, 6, 1), date(2025, 6, 2),
    date(2025, 10, 1), date(2025, 10, 2), date(2025, 10, 3), date(2025, 10, 4),
    date(2025, 10, 5), date(2025, 10, 6), date(2025, 10, 7), date(2025, 10, 8),
    # 2026
    date(2026, 1, 1), date(2026, 1, 2), date(2026, 2, 15), date(2026, 2, 16),
    date(2026, 2, 17), date(2026, 2, 18), date(2026, 2, 19), date(2026, 2, 20),
    date(2026, 2, 21), date(2026, 2, 22), date(2026, 2, 23), date(2026, 4, 4),
    date(2026, 4, 5), date(2026, 4, 6), date(2026, 5, 1), date(2026, 5, 2),
    date(2026, 5, 3), date(2026, 5, 4), date(2026, 5, 5), date(2026, 6, 19),
    date(2026, 6, 20), date(2026, 6, 21), date(2026, 9, 25), date(2026, 9, 26),
    date(2026, 9, 27), date(2026, 10, 1), date(2026, 10, 2), date(2026, 10, 3),
    date(2026, 10, 4), date(2026, 10, 5), date(2026, 10, 6), date(2026, 10, 7),
})


def _parse_occurred(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def is_peak(occurred_at: str | None) -> bool:
    """北京时间周一至周五 9–12、14–18 为高峰；周末与法定节假日全天空闲。"""
    dt = _parse_occurred(occurred_at)
    if dt is None:
        return False
    local = dt.astimezone(_BJ)
    if local.date() in _PRC_HOLIDAYS:
        return False
    if local.weekday() >= 5:
        return False
    minutes = local.hour * 60 + local.minute
    return (9 * 60 <= minutes < 12 * 60) or (14 * 60 <= minutes < 18 * 60)


def _model_key(model: str | None) -> str:
    """Match preset model ids by exact leaf name; avoid broad substring false positives."""
    raw = (model or '').casefold().strip()
    if not raw:
        return 'default'
    leaf = raw.rsplit('/', 1)[-1]
    if leaf in _MODEL_RATES:
        return leaf
    # DeepSeek 旧名仍按官方说明走 Flash
    if leaf in {'deepseek-v4-flash', 'deepseek-v4-flash-vision-exp'}:
        return 'deepseek-flash'
    return 'default'


def _usage_identity(model: str | None) -> tuple[str, str]:
    """Use recorded source ids; identify legacy bare preset names without session guesses."""
    raw = (model or '').strip().casefold()
    source, _, leaf = raw.rpartition('/')
    leaf = leaf or 'unknown'
    canonical = _model_key(leaf)
    name = canonical if canonical != 'default' else leaf
    if source:
        return source.removeprefix('my-'), name
    # Qwen's versioned model ids are qwen3.x/qwen4, without a separating dash.
    if name.startswith('qwen') and name[4:5].isdigit():
        return 'qwen', name
    provider = next((provider for provider in ('deepseek', 'qwen', 'glm') if name.startswith(provider + '-')), 'other')
    return provider, name


def _rates_for(model: str | None, *, peak: bool) -> dict[str, float]:
    key = _model_key(model)
    table = _MODEL_RATES.get(key)
    if not table:
        return dict(_DEFAULT_RATES)
    return dict(table['peak' if peak else 'off_peak'])


def cost_cny(
    model: str | None,
    input_tokens: int,
    output_tokens: int,
    *,
    cache_read_input_tokens: int | None = None,
    occurred_at: str | None = None,
) -> float:
    peak = is_peak(occurred_at)
    rates = _rates_for(model, peak=peak)
    inn = max(0, input_tokens)
    out = max(0, output_tokens)
    hit = min(inn, max(0, cache_read_input_tokens or 0))
    miss = inn - hit
    return (hit * rates['cache_hit'] + miss * rates['cache_miss'] + out * rates['output']) / 1_000_000


def _count(value: Any) -> int:
    return value if type(value) is int and value >= 0 else 0


def _session_title(record: dict[str, Any]) -> str:
    for message in record.get('messages') or []:
        if not isinstance(message, dict):
            continue
        content = str(message.get('content') or '').strip()
        if content:
            line = content.split('\n', 1)[0].strip()
            return line[:80] or record.get('id', '')[:8]
    return (record.get('id') or '')[:8]


def _owned_sessions() -> dict[str, dict[str, Any]]:
    owner = itam_bridge.owner() if itam_bridge.is_enabled() else None
    with d.db() as connection:
        if owner is not None:
            rows = connection.execute(
                "SELECT data FROM records WHERE kind=? AND json_extract(data,'$.owner_user_id') IS ?",
                ('session', owner),
            ).fetchall()
        else:
            rows = connection.execute("SELECT data FROM records WHERE kind=?", ('session',)).fetchall()
    result: dict[str, dict[str, Any]] = {}
    for (raw,) in rows:
        record = json.loads(raw)
        sid = record.get('id')
        if sid:
            result[sid] = record
    return result


def _generation_calls(owned: set[str], since: datetime) -> list[dict[str, Any]]:
    """One row per model_metrics, enriched with cache_read from the preceding usage event."""
    since_iso = since.astimezone(timezone.utc).isoformat()
    with d.db() as connection:
        rows = connection.execute(
            "SELECT data FROM records WHERE kind=? AND json_extract(data,'$.type') IN ('usage','model_metrics') "
            "AND json_extract(data,'$.occurred_at') >= ? ORDER BY id",
            ('event', since_iso),
        ).fetchall()

    return _calls_from_events((json.loads(raw) for (raw,) in rows), owned)


def _calls_from_events(events, owned: set[str]) -> list[dict[str, Any]]:
    last_usage: dict[str, dict[str, Any]] = {}
    calls: list[dict[str, Any]] = []
    for event in events:
        sid = event.get('session_id')
        if sid not in owned:
            continue
        result = event.get('result') or {}
        if not isinstance(result, dict):
            continue
        if event.get('type') == 'usage':
            if result.get('input_tokens') is None and result.get('output_tokens') is None:
                continue
            last_usage[sid] = result
            continue
        if event.get('type') != 'model_metrics':
            continue
        if result.get('input_tokens') is None and result.get('output_tokens') is None:
            continue
        usage = last_usage.get(sid) or {}
        inn = _count(result.get('input_tokens'))
        # 仅在 input 对齐时采信同轮 usage 的缓存命中数，避免串轮
        cache = None
        if usage.get('input_tokens') == result.get('input_tokens'):
            cache = usage.get('cache_read_input_tokens')
        calls.append({
            'session_id': sid,
            'occurred_at': event.get('occurred_at'),
            'model': str(result.get('model_id') or result.get('model') or '') or None,
            'input_tokens': inn,
            'output_tokens': _count(result.get('output_tokens')),
            'cache_read_input_tokens': _count(cache) if cache is not None else 0,
            'peak': is_peak(event.get('occurred_at')),
        })
    return calls


# Session cards poll frequently; only re-read the small event projection when
# a session journal or status changes. No messages, credentials or files are read.
_SESSION_TOTALS: dict[tuple[str, str], tuple[tuple, dict[str, Any]]] = {}


def session_summaries(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    for record in records:
        sid = record['id']
        key = (str(d.DATA.resolve()), sid)
        revision = (record.get('event_seq'), record.get('status'), record.get('updated_at'))
        cached = _SESSION_TOTALS.get(key)
        if cached and cached[0] == revision:
            record.update(cached[1])
            continue
        prefix = sid + ':'
        with d.db() as connection:
            rows = connection.execute(
                "SELECT json_object('session_id',json_extract(data,'$.session_id'),"
                "'type',json_extract(data,'$.type'),'occurred_at',json_extract(data,'$.occurred_at'),"
                "'status',json_extract(data,'$.status'),'result',json(CASE WHEN "
                "json_extract(data,'$.type') IN ('usage','model_metrics') THEN "
                "coalesce(json_extract(data,'$.result'),'{}') ELSE '{}' END)) "
                "FROM records WHERE kind=? AND id>? AND id<? AND json_extract(data,'$.type') "
                "IN ('usage','model_metrics','status','result','error','compacted') ORDER BY id",
                ('event', prefix, prefix + '~'),
            ).fetchall()
        events = [json.loads(row[0]) for row in rows]
        calls = _calls_from_events(events, {sid})
        cost = sum(cost_cny(call['model'], call['input_tokens'], call['output_tokens'],
                            cache_read_input_tokens=call['cache_read_input_tokens'],
                            occurred_at=call['occurred_at']) for call in calls)
        duration = 0.0
        started = None
        last_at = None
        has_run = False
        for event in events:
            at = _parse_occurred(event.get('occurred_at'))
            if at is None:
                continue
            last_at = at
            if event['type'] == 'status' and event.get('status') == 'running':
                if started is None:
                    started = at
                has_run = True
            elif event['type'] in ('result', 'error', 'compacted') or event['type'] == 'status':
                if started is not None:
                    duration += max(0, (at - started).total_seconds() * 1000)
                    started = None
        running_since = started if record.get('status') == 'running' else None
        if started is not None and running_since is None and last_at is not None:
            duration += max(0, (last_at - started).total_seconds() * 1000)
        unstarted = record.get('status') in ('idle', 'queued') and not has_run
        value = {
            'task_duration_ms': round(duration) if has_run or unstarted else None,
            'task_running_since': running_since.isoformat() if running_since else None,
            'task_cost_cny': cost if calls else (0.0 if unstarted else None),
        }
        _SESSION_TOTALS[key] = (revision, value)
        record.update(value)
    return records


def _empty_bucket() -> dict[str, Any]:
    return {
        'input_tokens': 0,
        'output_tokens': 0,
        'cache_read_input_tokens': 0,
        'total_tokens': 0,
        'calls': 0,
        'cost_cny': 0.0,
        'peak_calls': 0,
        'off_peak_calls': 0,
    }


def overview(*, days: int = 30, provider: str = '', model: str = '') -> dict[str, Any]:
    window = max(1, min(int(days or 30), 366))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=window - 1)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = _owned_sessions()
    calls = _generation_calls(set(sessions), since)

    # Options come only from preset prices and this owner's calls in the time window.
    choices = {_usage_identity(name) for name in _MODEL_RATES}
    choices.update(_usage_identity(call['model']) for call in calls)
    selected_provider, selected_model = provider.strip().casefold(), model.strip().casefold()
    if selected_provider or selected_model:
        calls = [call for call in calls if
                 (not selected_provider or _usage_identity(call['model'])[0] == selected_provider)
                 and (not selected_model or _usage_identity(call['model'])[1] == selected_model)]
    priced_models = {name for source, name in choices
                     if (not selected_provider or source == selected_provider)
                     and (not selected_model or name == selected_model)}

    by_day: dict[str, dict[str, Any]] = defaultdict(_empty_bucket)
    by_session: dict[str, dict[str, Any]] = defaultdict(
        lambda: {**_empty_bucket(), 'model': None, 'last_at': None},
    )

    for call in calls:
        inn = call['input_tokens']
        out = call['output_tokens']
        cache = call['cache_read_input_tokens']
        model = call['model']
        day = (call.get('occurred_at') or '')[:10]
        sid = call['session_id']
        cost = cost_cny(
            model, inn, out,
            cache_read_input_tokens=cache,
            occurred_at=call.get('occurred_at'),
        )

        for bucket in (by_day[day], by_session[sid]):
            bucket['input_tokens'] += inn
            bucket['output_tokens'] += out
            bucket['cache_read_input_tokens'] += cache
            bucket['total_tokens'] += inn + out
            bucket['calls'] += 1
            bucket['cost_cny'] += cost
            if call['peak']:
                bucket['peak_calls'] += 1
            else:
                bucket['off_peak_calls'] += 1

        sess = by_session[sid]
        if model:
            sess['model'] = model
        ts = call.get('occurred_at')
        if ts and (sess['last_at'] is None or ts > sess['last_at']):
            sess['last_at'] = ts

    day_axis: list[str] = []
    cursor = since.date()
    end = now.date()
    while cursor <= end:
        day_axis.append(cursor.isoformat())
        cursor += timedelta(days=1)

    daily = []
    for day in day_axis:
        row = by_day.get(day) or _empty_bucket()
        daily.append({
            'date': day,
            'input_tokens': row['input_tokens'],
            'output_tokens': row['output_tokens'],
            'cache_read_input_tokens': row['cache_read_input_tokens'],
            'total_tokens': row['total_tokens'],
            'calls': row['calls'],
            'peak_calls': row['peak_calls'],
            'off_peak_calls': row['off_peak_calls'],
            'cost_cny': round(row['cost_cny'], 4),
        })

    session_rows = []
    for sid, row in by_session.items():
        record = sessions.get(sid) or {}
        session_rows.append({
            'session_id': sid,
            'title': _session_title(record),
            'model_id': row.get('model') or record.get('model_id'),
            'input_tokens': row['input_tokens'],
            'output_tokens': row['output_tokens'],
            'cache_read_input_tokens': row['cache_read_input_tokens'],
            'total_tokens': row['total_tokens'],
            'calls': row['calls'],
            'peak_calls': row['peak_calls'],
            'off_peak_calls': row['off_peak_calls'],
            'cost_cny': round(row['cost_cny'], 4),
            'last_at': row['last_at'],
            'updated_at': record.get('updated_at'),
        })
    session_rows.sort(key=lambda item: item['total_tokens'], reverse=True)

    totals = {
        'input_tokens': sum(r['input_tokens'] for r in daily),
        'output_tokens': sum(r['output_tokens'] for r in daily),
        'cache_read_input_tokens': sum(r['cache_read_input_tokens'] for r in daily),
        'total_tokens': sum(r['total_tokens'] for r in daily),
        'calls': sum(r['calls'] for r in daily),
        'peak_calls': sum(r['peak_calls'] for r in daily),
        'off_peak_calls': sum(r['off_peak_calls'] for r in daily),
        'cost_cny': round(sum(r['cost_cny'] for r in daily), 4),
        'sessions': len(session_rows),
    }

    return {
        'days': window,
        'filters': {
            'providers': sorted({source for source, _ in choices}),
            'models': [{'provider': source, 'id': name} for source, name in sorted(choices)],
        },
        'currency': 'CNY',
        'cost_note': '按官方预设模型刊例估算（DeepSeek 含峰谷；Qwen/GLM 统一价），非账单',
        'pricing_source': 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing',
        'rates_cny_per_m': {
            model: {
                'off_peak': table['off_peak'],
                'peak': table['peak'],
            }
            for model, table in _MODEL_RATES.items() if model in priced_models
        },
        'peak_windows': {
            'timezone': 'Asia/Shanghai',
            'weekdays': 'Mon–Fri',
            'hours': ['09:00–12:00', '14:00–18:00'],
            'note': '仅 DeepSeek 区分峰谷：周末与中国法定节假日全天空闲；空闲价为高峰一半。Qwen/GLM 无峰谷。',
        },
        'totals': totals,
        'daily': daily,
        'sessions': session_rows,
    }
