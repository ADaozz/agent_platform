#!/usr/bin/env bash
# 部署脚本公共函数。由其它脚本 source，不单独执行。
set -euo pipefail

DEPLOY_ENV=${DEPLOY_ENV:-/etc/agent-platform/deploy.env}

log()  { printf '\n\033[1;34m==> %s\033[0m\n' "$*"; }
info() { printf '    %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*" >&2; }
die()  { printf '\033[1;31m[error]\033[0m %s\n' "$*" >&2; exit 1; }

require_root() {
  [ "$(id -u)" -eq 0 ] || die "需要 root 权限：sudo $0"
}

require_cmd() {
  local c
  for c in "$@"; do
    command -v "$c" >/dev/null 2>&1 || die "缺少命令：$c"
  done
}

# 加载 /etc/agent-platform/deploy.env 并派生常用变量
load_env() {
  [ -f "$DEPLOY_ENV" ] || die "找不到 $DEPLOY_ENV（先执行：cp deploy/deploy.env.example $DEPLOY_ENV 并按实际修改）"
  set -a
  # shellcheck disable=SC1090
  . "$DEPLOY_ENV"
  set +a
  : "${DOMAIN:?deploy.env 中 DOMAIN 不能为空}"
  : "${APP_ROOT:?deploy.env 中 APP_ROOT 不能为空}"
  : "${DATA_ROOT:?}"
  : "${ETC_ROOT:?}"
  : "${SERVICE_USER:?}"
  : "${BACKEND_PORT:?}"
  : "${RUNTIME_PORT:?}"
  : "${REDIS_PORT:?}"
  : "${TLS_CERT:?}"
  : "${TLS_KEY:?}"
  CERT_LOGIN_ENABLED=${CERT_LOGIN_ENABLED:-false}
  TLS_CLIENT_CA=${TLS_CLIENT_CA:-$ETC_ROOT/tls/client-ca-bundle.crt}
  ACME_WEBROOT=${ACME_WEBROOT:-/var/www/letsencrypt}
  REDIS_CONF=${REDIS_CONF:-/etc/redis/agent-platform.conf}
  REDIS_DATA_DIR=${REDIS_DATA_DIR:-/var/lib/redis/agent-platform}
  REDIS_LOG_DIR=${REDIS_LOG_DIR:-/var/log/redis}
  export REDIS_CONF REDIS_DATA_DIR REDIS_LOG_DIR

  # DOMAIN 允许直接填 IPv4（例如没域名、先用公网 IP 上线）：
  # 此时只能用自签证书，Let's Encrypt 不支持 IP，浏览器一定会提示证书不受信任。
  if is_ipv4 "$DOMAIN"; then
    SITE_IS_IP=true
    # 除公网 IP 外一并签上 localhost / 127.0.0.1：WSL2 的 localhostForwarding 会让
    # Windows 的 localhost 直通到容器内 nginx，本机验收常用这个地址，
    # SAN 里没有它浏览器会报 ERR_CERT_COMMON_NAME_INVALID（等于白导入根 CA）。
    # EXTRA_SAN 供追加其它地址，例如 EXTRA_SAN='IP:192.168.1.10'
    TLS_SAN="IP:$DOMAIN, IP:127.0.0.1, DNS:localhost"
    [ -n "${EXTRA_SAN:-}" ] && TLS_SAN="$TLS_SAN, ${EXTRA_SAN}"
  else
    SITE_IS_IP=false
    TLS_SAN="DNS:$DOMAIN"
  fi
  # IP + 自签证书时必须关掉 HSTS：否则浏览器记住"只走 https"后，
  # 用户连"继续访问（不安全）"都点不进去，等于把站点锁死。
  if [ "$SITE_IS_IP" = true ]; then
    HSTS_HEADER="# HSTS 未启用：IP + 自签证书场景强制 HSTS 会把浏览器锁死"
  else
    HSTS_HEADER='add_header Strict-Transport-Security "max-age=31536000" always;'
  fi

  WEB_ROOT="$APP_ROOT/current/frontend"
  BACKEND_ADDR="127.0.0.1:$BACKEND_PORT"
  PUBLIC_ORIGIN="https://$DOMAIN"
  REPO_ROOT=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
  # envsubst 只认导出的环境变量，派生变量必须 export
  export WEB_ROOT BACKEND_ADDR PUBLIC_ORIGIN REPO_ROOT SITE_IS_IP TLS_SAN HSTS_HEADER
}

is_ipv4() {
  case "$1" in
    '' | *[!0-9.]*) return 1 ;;
  esac
  local IFS=.
  set -- $1
  [ $# -eq 4 ] || return 1
  local o
  for o in "$@"; do
    [ "$o" -ge 0 ] 2>/dev/null && [ "$o" -le 255 ] || return 1
  done
  return 0
}

# write_self_signed_cert <cert> <key> <domain-or-ip> [天数] [SAN 列表]
# Chrome 对证书有效期上限是 398 天，超过会直接判无效，所以 IP 模式用 397。
write_self_signed_cert() {
  local cert=$1 key=$2 name=$3 days=${4:-397} san=${5:-}
  if [ -z "$san" ]; then
    if is_ipv4 "$name"; then san="IP:$name"; else san="DNS:$name"; fi
  fi
  install -d -m 700 "$(dirname "$cert")" "$(dirname "$key")"
  openssl req -x509 -nodes -newkey rsa:2048 -days "$days" -sha256 \
    -subj "/CN=$name" -addext "subjectAltName=$san" \
    -keyout "$key" -out "$cert" >/dev/null 2>&1
  chmod 600 "$key"
  chmod 644 "$cert"
}

# ca_available：本地 CA（init-ca.sh 生成，含中间 CA 私钥）是否可用于签服务端证书
ca_available() {
  [ -s "${ETC_ROOT:-}/ca/intermediate-ca.crt" ] && [ -s "${ETC_ROOT:-}/ca/intermediate-ca.key" ] &&
    [ -s "${ETC_ROOT:-}/ca/root-ca.crt" ]
}

# write_ca_signed_cert <cert> <key> <domain-or-ip> [天数] [SAN 列表]
# 用本地中间 CA 签服务端证书，fullchain = 叶子 + 中间 CA（根 CA 由客户端预先导入）。
# 比自签好：客户端只要导入一次 root-ca.crt，443 和 8443 的信任一次解决。
# CA 不可用或签发失败时返回 1，由调用方回退自签。
write_ca_signed_cert() {
  local cert=$1 key=$2 name=$3 days=${4:-825} san=${5:-} ca_dir ext csr tmp
  ca_available || return 1
  ca_dir=${ETC_ROOT}/ca
  if [ -z "$san" ]; then
    if is_ipv4 "$name"; then san="IP:$name"; else san="DNS:$name"; fi
  fi
  install -d -m 700 "$(dirname "$cert")" "$(dirname "$key")"
  # Chrome 对同一 subject 的证书会按序列号缓存，随机序列号避免重签后被当成旧证书
  csr=$(mktemp) && ext=$(mktemp) && tmp=$(mktemp)
  cat >"$ext" <<EOF
basicConstraints = critical,CA:FALSE
keyUsage = critical,digitalSignature,keyEncipherment
extendedKeyUsage = serverAuth
subjectAltName = $san
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid,issuer
EOF
  openssl genrsa -out "$key" 2048 2>/dev/null &&
    openssl req -new -key "$key" -subj "/C=CN/ST=Shanghai/L=Shanghai/O=personalDemo/OU=Web/CN=$name" -out "$csr" &&
    openssl x509 -req -in "$csr" -sha256 -days "$days" \
      -CA "$ca_dir/intermediate-ca.crt" -CAkey "$ca_dir/intermediate-ca.key" \
      -set_serial "0x$(openssl rand -hex 16)" \
      -extfile "$ext" -out "$tmp.crt" 2>/dev/null || {
    rm -f "$csr" "$ext" "$tmp" "$tmp.crt"
    return 1
  }
  # fullchain：nginx 的 ssl_certificate 需要把中间 CA 一起发出去
  cat "$tmp.crt" "$ca_dir/intermediate-ca.crt" >"$tmp"
  # 自检：叶子能由本地 CA 链验通（-untrusted 带中间 CA）
  openssl verify -CAfile "$ca_dir/root-ca.crt" -untrusted "$ca_dir/intermediate-ca.crt" "$tmp.crt" >/dev/null 2>&1 || {
    rm -f "$csr" "$ext" "$tmp" "$tmp.crt"
    return 1
  }
  rm -f "$csr" "$ext" "$tmp.crt"
  mv -f "$tmp" "$cert"
  chmod 600 "$key"
  chmod 644 "$cert"
  return 0
}

# secret_set <secrets.env> <KEY> <value>：存在则替换，不存在则追加
secret_set() {
  local file=$1 key=$2 value=$3
  [ -f "$file" ] || return 0
  if grep -q "^${key}=" "$file"; then
    # 用 | 作分隔符，避免密钥里的 / 破坏 sed 表达式
    local esc=${value//\\/\\\\}
    esc=${esc//|/\\|}
    esc=${esc//&/\\&}
    sed -i "s|^${key}=.*|${key}=${esc}|" "$file"
  else
    printf '%s=%s\n' "$key" "$value" >>"$file"
  fi
}

# render <模板> <目标> <权限> <允许替换的变量名...>
# 只替换显式列出的变量，避免把 ${JAVA_OPTS} 之类系统变量提前吃掉
render() {
  local tpl=$1 dest=$2 mode=$3
  shift 3
  local list= v
  for v in "$@"; do
    # envsubst 只认环境变量：变量存在但没 export 时会被替换成空串而不报错，
    # 结果就是 requirepass 后面空着、配置看起来合法但服务起不来。
    # 用 printenv（只读环境变量）而不是 ${!v}（读 shell 变量）才能真正拦住。
    [ -n "$(printenv "$v" 2>/dev/null || true)" ] ||
      die "渲染 $(basename "$tpl") 时环境变量 $v 为空（检查是否漏了 export）"
    list="$list\${$v}"
  done
  mkdir -p "$(dirname "$dest")"
  envsubst "$list" <"$tpl" >"$dest.tmp"
  # 渲染后不应残留占位符
  if grep -qE '\$\{[A-Z_][A-Z0-9_]*\}' "$dest.tmp"; then
    warn "模板 $tpl 渲染后仍有未替换变量：$(grep -oE '\$\{[A-Z_][A-Z0-9_]*\}' "$dest.tmp" | sort -u | tr '\n' ' ')"
  fi
  chmod "$mode" "$dest.tmp"
  mv -f "$dest.tmp" "$dest"
}

# 读取 secrets.env 中的单个值（不 source，避免覆盖当前环境）
secret_get() {
  local file=$1 key=$2
  [ -f "$file" ] || return 0
  sed -n "s/^${key}=//p" "$file" | tail -1
}

gen_secret() {
  openssl rand -base64 48 | tr -d '\n'
}

# wait_backend [超时秒]：轮询后端公开接口，直到它真正能响应。
# 后端重启后 Spring Boot 要 20-60 秒才监听（SQLite 建表/schema 检查 + data.sql 幂等脚本），
# 这段窗口内 healthcheck 会报 backend 000、/api 502、8443 502 —— 全是假失败，
# set-admin.sh 改完库重启后端后立刻验收最容易撞上。
wait_backend() {
  local timeout=${1:-90} i=0 code
  command -v curl >/dev/null 2>&1 || return 0
  while [ "$i" -lt "$timeout" ]; do
    code=$(curl -s -o /dev/null -m 3 -w '%{http_code}' \
      "http://127.0.0.1:${BACKEND_PORT:-8080}/login/cert/availability" 2>/dev/null) || true
    [ "$code" = "200" ] && return 0
    sleep 2
    i=$((i + 2))
  done
  return 1
}
