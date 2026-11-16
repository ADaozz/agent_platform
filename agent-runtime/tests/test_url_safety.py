"""Personal model SSRF guards: save-time and call-time enforcement."""
import ipaddress

import pytest

from platform_app import domain as d, models as m
from platform_app import url_safety


@pytest.fixture(autouse=True)
def data(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DATA', tmp_path)
    for name in ('PLATFORM_CONFIG', 'PLATFORM_MODEL', 'PLATFORM_API_KEY', 'PLATFORM_BASE_URL', 'PERSONAL_MODEL_ALLOWED_HOSTS'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(url_safety, '_host_ips', lambda host: [ipaddress.ip_address('93.184.216.34')])


def source(base_url='https://llm.example.com/v1', key='sk-personal'):
    return {'base_url': base_url, 'api_key': key, 'api': 'chat_completions', 'models': {'chat': {}}}


@pytest.mark.parametrize('base_url', [
    'http://llm.example.com/v1',
    'https://127.0.0.1/v1',
    'https://10.0.0.8/v1',
    'https://169.254.169.254/latest',
    'https://localhost/v1',
])
def test_personal_save_rejects_unsafe_endpoints(base_url):
    with pytest.raises(ValueError):
        m.save_personal('1001', {'default': 'mine/chat', 'models': {'mine': source(base_url=base_url)}}, 0)


def test_personal_save_accepts_public_https():
    m.save_personal('1001', {'default': 'mine/chat', 'models': {'mine': source()}}, 0)
    assert m.public_personal('1001')['profiles'][0]['id'] == 'mine/chat'
    assert m.options('1001')['default'] == 'my-mine/chat'


def test_legacy_private_config_cannot_bypass_at_call_time(tmp_path, monkeypatch):
    monkeypatch.setattr(d, 'DATA', tmp_path)
    # Bypass save-time checks to simulate a legacy unsafe row.
    sealed = m.seal({'default': 'mine/chat', 'models': {'mine': source(base_url='https://127.0.0.1/v1')}})
    d.put('user_model_config', {'id': '1001', 'revision': 1, 'encrypted': sealed})
    with pytest.raises(ValueError):
        m.merged('1001')
    with pytest.raises(ValueError):
        m.selection('my-mine/chat', owner='1001')


def test_allowlist_rejects_unlisted_public_host(monkeypatch):
    monkeypatch.setenv('PERSONAL_MODEL_ALLOWED_HOSTS', 'api.openai.com')
    with pytest.raises(ValueError, match='允许名单'):
        m.save_personal('1001', {'default': 'mine/chat', 'models': {'mine': source()}}, 0)


def test_dns_to_private_address_is_rejected(monkeypatch):
    monkeypatch.setattr(url_safety, '_host_ips', lambda host: [ipaddress.ip_address('10.1.2.3')])
    with pytest.raises(ValueError, match='私网|链路本地|回环'):
        url_safety.assert_safe_personal_base_url('https://evil.example.com/v1')
