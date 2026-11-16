#!/usr/bin/env bash
# 健康检查：redis / 后端 / runtime / nginx / 磁盘。全部正常返回 0。
# 普通用户即可运行，release.sh 用它判断发布是否成功。
#
#   deploy/scripts/healthcheck.sh [--quiet]
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"
load_env

QUIET=false
[ "${1:-}" = "--quiet" ] && QUIET=true
say() { [ "$QUIET" = true ] || printf '%s\n' "$*"; }
fail=0
check() { # check <名称> <0/1>
  if [ "$2" -eq 1 ]; then
    say "  [ok]   $1"
  else
    say "  [FAIL] $1"
    fail=$((fail + 1))
  fi
}

http_code() { # http_code <url> [curl 参数...]
  local url=$1 code
  shift
  code=$(curl -s -o /dev/null -m 8 -w '%{http_code}' "$url" "$@" 2>/dev/null) || true
  # curl 连不上时 -w 已经输出 000，这里只兜底完全没输出的情况
  [ -n "$code" ] || code=000
  printf '%s' "$code"
}

say "健康检查 $(date -Is)"

# Redis：会话与验证码都在这
REDIS_PASSWORD=$(secret_get "$ETC_ROOT/secrets.env" REDIS_PASSWORD)
if command -v redis-cli >/dev/null 2>&1 && [ -n "$REDIS_PASSWORD" ]; then
  pong=$(REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli -h 127.0.0.1 -p "$REDIS_PORT" ping 2>/dev/null | tr -d '\r')
  [ "$pong" = "PONG" ] && check "redis 127.0.0.1:$REDIS_PORT" 1 || check "redis 127.0.0.1:$REDIS_PORT" 0
else
  check "redis-cli 不可用" 0
fi

# 后端：匿名端点 /login/cert/availability
# 刚重启过（set-admin.sh / release.sh 之后）会有几十秒启动窗口，先等就绪再判，
# 否则会同时报 backend 000、/api 502、8443 502 三项假失败。
if command -v curl >/dev/null 2>&1 && ! wait_backend 90; then
  say "         （后端 90 秒内未就绪，可能是启动失败：journalctl -u agent-platform-backend -n 50）"
fi
code=$(http_code "http://127.0.0.1:$BACKEND_PORT/login/cert/availability")
[ "$code" = "200" ] && check "backend :$BACKEND_PORT /login/cert/availability" 1 || check "backend :$BACKEND_PORT（HTTP $code）" 0

# Runtime：多用户模式下 /api/status 需要签名，401 也说明进程活着
code=$(http_code "http://127.0.0.1:$RUNTIME_PORT/api/status")
case "$code" in
  200 | 401) check "agent-runtime :$RUNTIME_PORT" 1 ;;
  *) check "agent-runtime :$RUNTIME_PORT（HTTP $code）" 0 ;;
esac

# Nginx：https 首页 + /api 反代
# IP 模式下 curl 的 --resolve 对 IP 字面量无效（URL 里是 IP 时不走解析表），
# 所以改为直连本机 443 并带上 Host 头，测的是 nginx 这一段链路。
nginx_code() { # nginx_code <path>
  if [ "$SITE_IS_IP" = true ]; then
    http_code "https://127.0.0.1:443$1" -k -H "Host: $DOMAIN"
  else
    http_code "https://$DOMAIN:443$1" --resolve "$DOMAIN:443:127.0.0.1" -k
  fi
}
if command -v curl >/dev/null 2>&1; then
  code=$(nginx_code "/")
  if [ "$code" = "200" ]; then
    check "nginx https://$DOMAIN/" 1
  else
    check "nginx https://$DOMAIN/（HTTP $code）" 0
    if [ "$code" = "404" ]; then
      say "         → 404 多半是权限：$APP_ROOT 或 $APP_ROOT/releases 为 750 时 www-data 无法穿越，"
      say "           修：sudo chmod 755 $APP_ROOT $APP_ROOT/releases && sudo chmod -R o+rX $APP_ROOT/current/"
    fi
  fi
  code=$(nginx_code "/api/login/cert/availability")
  [ "$code" = "200" ] && check "nginx /api -> backend" 1 || check "nginx /api -> backend（HTTP $code）" 0

  # 8443：只放行 = /login/cert。不带客户端证书时后端返回表单页（200），
  # 说明 nginx 的 ssl_verify_client optional_no_ca 与反代都正常。
  if [ "${CERT_LOGIN_ENABLED:-false}" = true ]; then
    if [ "$SITE_IS_IP" = true ]; then
      code=$(http_code "https://127.0.0.1:8443/login/cert" -k -H "Host: $DOMAIN")
      code2=$(http_code "https://127.0.0.1:8443/api/user/info" -k -H "Host: $DOMAIN")
    else
      code=$(http_code "https://$DOMAIN:8443/login/cert" --resolve "$DOMAIN:8443:127.0.0.1" -k)
      code2=$(http_code "https://$DOMAIN:8443/api/user/info" --resolve "$DOMAIN:8443:127.0.0.1" -k)
    fi
    [ "$code" = "200" ] && check "nginx https://$DOMAIN:8443/login/cert" 1 ||
      check "nginx https://$DOMAIN:8443/login/cert（HTTP $code）" 0
    [ "$code2" = "404" ] && check "nginx :8443 其它路径仍 404" 1 ||
      check "nginx :8443 其它路径应 404（HTTP $code2）" 0
  fi
fi

# 磁盘：低于 10% 可用就报警
avail=$(df --output=pcent "$DATA_ROOT" 2>/dev/null | tail -1 | tr -dc '0-9')
[ "${avail:-100}" -lt 90 ] && check "磁盘 $DATA_ROOT 已用 ${avail}%" 1 || check "磁盘 $DATA_ROOT 已用 ${avail}%（>90%）" 0

if [ "$fail" -eq 0 ]; then
  say "全部通过"
  exit 0
fi
say "$fail 项异常"
exit 1
