"""Aggregate model token usage from durable model_metrics journal events.

Usage events stream intermediate counts and may duplicate a completed call; model_metrics
is emitted once per generation. Cache-hit counts are taken from the paired usage event
immediately before each metrics snapshot.

DeepSeek Flash costs follow https://api-docs.deepseek.com/zh-cn/quick_start/pricing
(cache hit/miss × peak/off-peak). Estimates are not provider invoices.
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

# 元 / 百万 tokens — DeepSeek 官方刊例（deepseek-flash / deepseek-v4-pro）
# 空闲 = 高峰一半；高峰：北京时间周一至周五 9–12、14–18（不含法定节假日）
_DEEPSEEK_RATES: dict[str, dict[str, dict[str, float]]] = {
    'deepseek-flash': {
        'off_peak': {'cache_hit': 0.02, 'cache_miss': 1.0, 'output': 4.0},
        'peak': {'cache_hit': 0.04, 'cache_miss': 2.0, 'output': 8.0},
    },
    'deepseek-v4-pro': {
        'off_peak': {'cache_hit': 0.15, 'cache_miss': 4.5, 'output': 13.5},
        'peak': {'cache_hit': 0.30, 'cache_miss': 9.0, 'output': 27.0},
    },
}

# 未知模型兜底：按 Flash 空闲未命中 / 输出估算
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
    key = (model or '').casefold()
    if 'v4-pro' in key or 'v4_pro' in key or key.endswith('/deepseek-v4-pro'):
        return 'deepseek-v4-pro'
    if 'flash' in key or 'deepseek' in key:
        # 旧名 deepseek-v4-flash 等按官方说明走 Flash 价
        return 'deepseek-flash'
    return 'default'


def _rates_for(model: str | None, *, peak: bool) -> dict[str, float]:
    key = _model_key(model)
    table = _DEEPSEEK_RATES.get(key)
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

    last_usage: dict[str, dict[str, Any]] = {}
    calls: list[dict[str, Any]] = []
    for (raw,) in rows:
        event = json.loads(raw)
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
            'model': str(result.get('model') or '') or None,
            'input_tokens': inn,
            'output_tokens': _count(result.get('output_tokens')),
            'cache_read_input_tokens': _count(cache) if cache is not None else 0,
            'peak': is_peak(event.get('occurred_at')),
        })
    return calls


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


def overview(*, days: int = 30) -> dict[str, Any]:
    window = max(1, min(int(days or 30), 366))
    now = datetime.now(timezone.utc)
    since = now - timedelta(days=window - 1)
    since = since.replace(hour=0, minute=0, second=0, microsecond=0)

    sessions = _owned_sessions()
    calls = _generation_calls(set(sessions), since)

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
            'model_id': record.get('model_id') or row.get('model'),
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
        'currency': 'CNY',
        'cost_note': '按 DeepSeek 官方刊例估算（缓存命中×峰谷），非账单',
        'pricing_source': 'https://api-docs.deepseek.com/zh-cn/quick_start/pricing',
        'rates_cny_per_m': {
            model: {
                'off_peak': table['off_peak'],
                'peak': table['peak'],
            }
            for model, table in _DEEPSEEK_RATES.items()
        },
        'peak_windows': {
            'timezone': 'Asia/Shanghai',
            'weekdays': 'Mon–Fri',
            'hours': ['09:00–12:00', '14:00–18:00'],
            'note': '周末与中国法定节假日全天空闲；空闲价为高峰一半',
        },
        'totals': totals,
        'daily': daily,
        'sessions': session_rows,
    }
