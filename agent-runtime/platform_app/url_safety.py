"""Personal-model endpoint safety: block SSRF via private/link-local/loopback targets."""
from __future__ import annotations

import ipaddress
import os
import socket
from urllib.parse import urlsplit


def allowed_personal_hosts() -> set[str] | None:
    """Comma-separated HTTPS host allowlist. Empty means any public host is allowed."""
    raw = os.environ.get('PERSONAL_MODEL_ALLOWED_HOSTS', '').strip()
    if not raw:
        return None
    return {item.strip().lower() for item in raw.split(',') if item.strip()}


def _host_ips(hostname: str) -> list[ipaddress._BaseAddress]:
    try:
        infos = socket.getaddrinfo(hostname, None, type=socket.SOCK_STREAM)
    except socket.gaierror as exc:
        raise ValueError(f'无法解析个人模型主机名：{hostname}') from exc
    addresses: list[ipaddress._BaseAddress] = []
    for info in infos:
        addr = info[4][0]
        try:
            addresses.append(ipaddress.ip_address(addr))
        except ValueError:
            continue
    if not addresses:
        raise ValueError(f'无法解析个人模型主机名：{hostname}')
    return addresses


def is_blocked_ip(address: ipaddress._BaseAddress) -> bool:
    return bool(
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
        or (getattr(address, 'is_site_local', False))
    )


def assert_safe_personal_base_url(url: str, *, resolve_dns: bool = True) -> str:
    """Reject non-HTTPS, credentialed, and non-public endpoints used by personal models."""
    if not isinstance(url, str) or not url.strip():
        raise ValueError('base_url 不能为空')
    parsed = urlsplit(url.strip())
    if parsed.scheme.lower() != 'https':
        raise ValueError('个人模型 base_url 必须使用 https:// 公网地址')
    if parsed.username or parsed.password:
        raise ValueError('个人模型 base_url 不得包含用户名或密码')
    host = parsed.hostname
    if not host:
        raise ValueError('个人模型 base_url 缺少主机名')
    host_key = host.lower().rstrip('.')
    if host_key in {'localhost', 'metadata.google.internal'}:
        raise ValueError('个人模型 base_url 不允许指向本机或元数据地址')

    allow = allowed_personal_hosts()
    if allow is not None and host_key not in allow:
        raise ValueError(f'个人模型主机不在允许名单中：{host_key}')

    try:
        literal = ipaddress.ip_address(host)
    except ValueError:
        literal = None
    if literal is not None and is_blocked_ip(literal):
        raise ValueError('个人模型 base_url 不允许指向回环、私网或链路本地地址')

    if resolve_dns and literal is None:
        for address in _host_ips(host_key):
            if is_blocked_ip(address):
                raise ValueError('个人模型 base_url 解析到了回环、私网或链路本地地址')
    return url.strip()


def walk_personal_base_urls(config: dict):
    """Yield every base_url string under a personal model config."""
    models = config.get('models') if isinstance(config, dict) else None
    if not isinstance(models, dict):
        return
    for group in models.values():
        if isinstance(group, dict) and isinstance(group.get('base_url'), str):
            yield group['base_url']
