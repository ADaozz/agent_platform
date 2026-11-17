from platform_app import usage_stats


def test_peak_windows_beijing():
    # 北京时间周一 10:00 = 高峰
    assert usage_stats.is_peak('2026-11-16T02:00:00+00:00') is True  # 10:00 CST
    # 北京时间周一 13:00 = 空闲
    assert usage_stats.is_peak('2026-11-16T05:00:00+00:00') is False  # 13:00 CST
    # 北京时间周一 15:00 = 高峰
    assert usage_stats.is_peak('2026-11-16T07:00:00+00:00') is True  # 15:00 CST
    # 周末全天空闲
    assert usage_stats.is_peak('2026-11-15T02:00:00+00:00') is False  # Sunday 10:00 CST


def test_flash_cache_and_peak_cost():
    # 空闲：1M hit + 0 miss + 1M out = 0.02 + 4 = 4.02
    assert abs(usage_stats.cost_cny(
        'deepseek-flash', 1_000_000, 1_000_000,
        cache_read_input_tokens=1_000_000,
        occurred_at='2026-11-15T02:00:00+00:00',  # Sunday off-peak
    ) - 4.02) < 1e-9
    # 高峰：0.5M hit + 0.5M miss + 1M out = 0.02 + 1.0 + 8 = 9.02
    assert abs(usage_stats.cost_cny(
        'deepseek/deepseek-flash', 1_000_000, 1_000_000,
        cache_read_input_tokens=500_000,
        occurred_at='2026-11-16T02:00:00+00:00',  # Mon 10:00 peak
    ) - 9.02) < 1e-9
    # 无缓存字段时整段按未命中
    assert abs(usage_stats.cost_cny(
        'deepseek-flash', 1_000_000, 0,
        occurred_at='2026-11-15T02:00:00+00:00',
    ) - 1.0) < 1e-9


def test_qwen_glm_flat_rates_ignore_peak():
    # qwen3.8-flash：1M hit + 0 miss + 1M out = 0.16 + 2.7 = 2.86（峰谷同价）
    off = usage_stats.cost_cny(
        'qwen/qwen3.8-flash', 1_000_000, 1_000_000,
        cache_read_input_tokens=1_000_000,
        occurred_at='2026-11-15T02:00:00+00:00',
    )
    peak = usage_stats.cost_cny(
        'qwen/qwen3.8-flash', 1_000_000, 1_000_000,
        cache_read_input_tokens=1_000_000,
        occurred_at='2026-11-16T02:00:00+00:00',
    )
    assert abs(off - 2.86) < 1e-9
    assert abs(peak - off) < 1e-9
    # glm-5.3：全未命中 8 + 输出 28
    assert abs(usage_stats.cost_cny('glm/glm-5.3', 1_000_000, 1_000_000) - 36.0) < 1e-9
    assert usage_stats._model_key('my-custom/other-flash') == 'default'


def test_session_title_prefers_first_user_line():
    title = usage_stats._session_title({
        'id': 'abcdef12xxxx',
        'messages': [{'role': 'user', 'content': '第一行标题\n其余内容'}],
    })
    assert title == '第一行标题'
    assert usage_stats._session_title({'id': 'abcdef12xxxx', 'messages': []}) == 'abcdef12'


def test_usage_filters_aggregate_actual_calls_and_keep_owner_isolation(tmp_path, monkeypatch):
    from datetime import datetime, timezone
    from platform_app import domain as d, itam_bridge
    monkeypatch.setattr(d, 'DATA', tmp_path)
    monkeypatch.setattr(itam_bridge, 'is_enabled', lambda: True)
    monkeypatch.setattr(itam_bridge, 'owner', lambda: '1001')
    now = datetime.now(timezone.utc).isoformat()
    d.put('session', {'id': 'owned', 'owner_user_id': '1001', 'model_id': 'qwen/qwen3.8-flash'})
    d.put('session', {'id': 'private', 'owner_user_id': '1002'})
    for index, (sid, model, inn, out) in enumerate([
        ('owned', 'deepseek/deepseek-flash', 1000, 100),
        ('owned', 'my-qwen/qwen3.8-flash', 2000, 200),
        ('owned', 'custom/other-model', 3000, 300),
        ('private', 'private-provider/private-model', 9999, 9999),
    ]):
        d.put('event', {'id': f'{sid}:{index:010}', 'session_id': sid,
                        'type': 'model_metrics', 'occurred_at': now,
                        'result': {'model_id': model, 'model': model.rsplit('/', 1)[-1],
                                   'input_tokens': inn, 'output_tokens': out}})
    all_usage = usage_stats.overview(days=7)
    assert all_usage['totals']['total_tokens'] == 6600
    assert all_usage['totals']['calls'] == 3
    assert 'private-provider' not in all_usage['filters']['providers']
    assert not any(item['id'] == 'private-model' for item in all_usage['filters']['models'])
    deepseek = usage_stats.overview(days=7, provider='deepseek')
    assert deepseek['totals']['total_tokens'] == 1100
    assert deepseek['totals']['calls'] == 1
    assert deepseek['totals']['sessions'] == 1
    assert deepseek['sessions'][0]['model_id'] == 'deepseek/deepseek-flash'
    assert sum(row['total_tokens'] for row in deepseek['daily']) == 1100
    assert set(deepseek['rates_cny_per_m']) == {'deepseek-flash', 'deepseek-v4-pro'}
    qwen = usage_stats.overview(days=7, provider='qwen', model='qwen3.8-flash')
    assert qwen['totals']['total_tokens'] == 2200
    assert set(qwen['rates_cny_per_m']) == {'qwen3.8-flash'}
    assert qwen['filters'] == all_usage['filters']
    missing = usage_stats.overview(days=7, provider='deepseek', model='qwen3.8-flash')
    assert missing['totals']['total_tokens'] == 0
    assert missing['totals']['sessions'] == 0
    assert missing['rates_cny_per_m'] == {}
    assert len(missing['daily']) == 7


def test_usage_identity_handles_legacy_names_and_custom_sources():
    assert usage_stats._usage_identity('deepseek-v4-flash') == ('deepseek', 'deepseek-flash')
    assert usage_stats._usage_identity('my-deepseek/deepseek-flash') == ('deepseek', 'deepseek-flash')
    assert usage_stats._usage_identity('gateway/deepseek-flash') == ('gateway', 'deepseek-flash')
    assert usage_stats._usage_identity('custom-model') == ('other', 'custom-model')
    for model in ('qwen3.8-flash', 'qwen3.7-plus', 'qwen4-max', 'qwen-max'):
        assert usage_stats._usage_identity(model) == ('qwen', model)


def test_session_cards_sum_execution_intervals_and_cache_unchanged_events(tmp_path, monkeypatch):
    from platform_app import domain as d
    monkeypatch.setattr(d, 'DATA', tmp_path)
    events = [
        ('status', '2026-11-17T01:00:00+00:00', {'status': 'running'}),
        ('model_metrics', '2026-11-17T01:00:19+00:00', {'result': {'model': 'deepseek-flash', 'input_tokens': 1000, 'output_tokens': 100}}),
        ('result', '2026-11-17T01:00:20+00:00', {'status': 'waiting_human'}),
        ('status', '2026-11-17T02:00:00+00:00', {'status': 'running'}),
        ('model_metrics', '2026-11-17T02:00:29+00:00', {'result': {'model': 'deepseek-flash', 'input_tokens': 1000, 'output_tokens': 100}}),
        ('result', '2026-11-17T02:00:30+00:00', {'status': 'completed'}),
    ]
    for seq, (kind, at, extra) in enumerate(events, 1):
        d.put('event', {'id': f'card:{seq:010}', 'session_id': 'card', 'type': kind, 'occurred_at': at, **extra})
    record = {'id': 'card', 'event_seq': 6, 'status': 'completed', 'updated_at': events[-1][1]}
    summary = usage_stats.session_summaries([dict(record)])[0]
    assert summary['task_duration_ms'] == 50000
    assert summary['task_running_since'] is None
    assert summary['task_cost_cny'] == sum(usage_stats.cost_cny('deepseek-flash', 1000, 100, occurred_at=at) for kind, at, _ in events if kind == 'model_metrics')
    with monkeypatch.context() as cached:
        def no_query():
            raise AssertionError('Unchanged cards must not reload their journals')
        cached.setattr(d, 'db', no_query)
        assert usage_stats.session_summaries([dict(record)])[0] == summary
    d.put('event', {'id': 'card:0000000007', 'session_id': 'card', 'type': 'status', 'status': 'running', 'occurred_at': '2026-11-18T01:00:00+00:00'})
    running = usage_stats.session_summaries([{**record, 'event_seq': 7, 'status': 'running'}])[0]
    assert running['task_duration_ms'] == 50000
    assert running['task_running_since'] == '2026-11-18T01:00:00+00:00'
    assert running['task_cost_cny'] == summary['task_cost_cny']


def test_session_card_unknown_legacy_metrics_are_not_zero(tmp_path, monkeypatch):
    from platform_app import domain as d
    monkeypatch.setattr(d, 'DATA', tmp_path)
    legacy, empty = usage_stats.session_summaries([
        {'id': 'legacy', 'status': 'completed', 'event_seq': 0},
        {'id': 'empty', 'status': 'idle', 'event_seq': 0},
    ])
    assert legacy['task_duration_ms'] is None and legacy['task_cost_cny'] is None
    assert empty['task_duration_ms'] == 0 and empty['task_cost_cny'] == 0


def test_preset_catalog_assigns_versioned_qwen_models_to_qwen(monkeypatch):
    monkeypatch.setattr(usage_stats, '_owned_sessions', lambda: {})
    monkeypatch.setattr(usage_stats, '_generation_calls', lambda *_: [])
    overview = usage_stats.overview(provider='qwen')
    assert set(overview['filters']['providers']) == {'deepseek', 'qwen', 'glm'}
    assert set(overview['rates_cny_per_m']) == {'qwen3.8-flash', 'qwen3.7-plus', 'qwen4-max'}
    qwen_options = [item for item in overview['filters']['models'] if item['id'].startswith('qwen')]
    assert len(qwen_options) == 3
    assert all(item['provider'] == 'qwen' for item in qwen_options)
