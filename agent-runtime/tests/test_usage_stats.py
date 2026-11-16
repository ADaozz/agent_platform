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


def test_session_title_prefers_first_user_line():
    title = usage_stats._session_title({
        'id': 'abcdef12xxxx',
        'messages': [{'role': 'user', 'content': '第一行标题\n其余内容'}],
    })
    assert title == '第一行标题'
    assert usage_stats._session_title({'id': 'abcdef12xxxx', 'messages': []}) == 'abcdef12'
