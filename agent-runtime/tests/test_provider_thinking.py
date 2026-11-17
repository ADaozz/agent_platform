from platform_app.agent_core.llm import provider_chat_extras


def test_deepseek_thinking_extras():
    enabled = provider_chat_extras('https://api.deepseek.com/v1', 'high')
    assert enabled['reasoning_effort'] == 'high'
    assert enabled['extra_body'] == {'thinking': {'type': 'enabled'}}
    disabled = provider_chat_extras('https://api.deepseek.com/v1', 'none')
    assert disabled['extra_body'] == {'thinking': {'type': 'disabled'}}


def test_qwen_enable_thinking_extras():
    on = provider_chat_extras('https://dashscope.aliyuncs.com/compatible-mode/v1', 'high')
    assert on['extra_body'] == {'enable_thinking': True}
    assert on['reasoning_effort'] == 'high'
    off = provider_chat_extras('https://dashscope.aliyuncs.com/compatible-mode/v1', 'disabled')
    assert off['extra_body'] == {'enable_thinking': False}
    assert 'reasoning_effort' not in off


def test_glm_thinking_extras():
    on = provider_chat_extras('https://open.bigmodel.cn/api/paas/v4', 'max')
    assert on['reasoning_effort'] == 'max'
    assert on['extra_body'] == {'thinking': {'type': 'enabled'}}


def test_custom_provider_passes_effort_only():
    extras = provider_chat_extras('https://api.openai.com/v1', 'high')
    assert extras == {'reasoning_effort': 'high'}
