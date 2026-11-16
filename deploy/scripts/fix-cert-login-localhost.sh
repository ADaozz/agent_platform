#!/usr/bin/env bash
# 一次性：把 https://localhost 加进证书登录回跳白名单并重启后端。
# 用法：sudo bash deploy/scripts/fix-cert-login-localhost.sh
set -euo pipefail
ENV=/etc/agent-platform/backend.env
[[ -f "$ENV" ]] || { echo "missing $ENV"; exit 1; }
if grep -q 'CERT_LOGIN_ALLOWED_ORIGINS=.*https://localhost' "$ENV"; then
  echo "already has https://localhost in ALLOWED_ORIGINS"
else
  sed -i 's|^CERT_LOGIN_ALLOWED_ORIGINS=\(.*\)$|CERT_LOGIN_ALLOWED_ORIGINS=\1,https://localhost|' "$ENV"
  # de-dup if DOMAIN was already localhost
  python3 - <<'PY'
from pathlib import Path
p = Path("/etc/agent-platform/backend.env")
lines = []
for line in p.read_text().splitlines():
    if line.startswith("CERT_LOGIN_ALLOWED_ORIGINS="):
        raw = line.split("=", 1)[1]
        seen, out = set(), []
        for part in raw.split(","):
            part = part.strip()
            if part and part not in seen:
                seen.add(part); out.append(part)
        line = "CERT_LOGIN_ALLOWED_ORIGINS=" + ",".join(out)
    lines.append(line)
p.write_text("\n".join(lines) + "\n")
PY
  echo "updated ALLOWED_ORIGINS:"
fi
grep '^CERT_LOGIN_' "$ENV"
# backend unit also needs AF_NETLINK (JDK)
UNIT=/etc/systemd/system/agent-platform-backend.service
if [[ -f "$UNIT" ]] && grep -q 'RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6$' "$UNIT"; then
  sed -i 's/RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6$/RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6 AF_NETLINK/' "$UNIT"
  systemctl daemon-reload
fi
systemctl restart agent-platform-backend
sleep 2
systemctl is-active agent-platform-backend
curl -sf http://127.0.0.1:8080/login/cert/availability
echo
echo "verify redirect → localhost (expect Location: https://localhost/login?...):"
curl -sk -D - -o /dev/null 'https://127.0.0.1:8443/login/cert?redirect=1&origin=https%3A%2F%2Flocalhost' \
  -H 'Host: localhost' -X POST | head -15
