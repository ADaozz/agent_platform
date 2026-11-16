#!/usr/bin/env bash
# 证书管理：
#   域名模式（DOMAIN 是域名）：向 Let's Encrypt 申请/续期，续期由 certbot.timer 自动完成
#    IP 模式（DOMAIN 是 IPv4）：Let's Encrypt 不支持 IP，用本地 CA（init-ca.sh）签发；
#                              没有本地 CA 私钥时才退回自签
#
#   sudo deploy/scripts/issue-tls-cert.sh                # 域名：申请 Let's Encrypt 证书
#   sudo deploy/scripts/issue-tls-cert.sh --dry-run      # 域名：先演练，不消耗配额
#   sudo deploy/scripts/issue-tls-cert.sh --local-ca     # 用本地 CA 重签服务端证书（IP 模式默认）
#   sudo deploy/scripts/issue-tls-cert.sh --self-signed  # 强制重签自签证书
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"

require_root
load_env
export DEBIAN_FRONTEND=noninteractive

DRY_RUN=false
SELF_SIGNED=false
LOCAL_CA=false
for a in "$@"; do
  case "$a" in
    --dry-run) DRY_RUN=true ;;
    --self-signed) SELF_SIGNED=true ;;
    --local-ca) LOCAL_CA=true ;;
    *) die "未知参数：$a（可用：--dry-run / --local-ca / --self-signed）" ;;
  esac
done

reload_nginx() {
  nginx -t || die "Nginx 配置检查失败，证书未生效"
  systemctl reload nginx
}

# --------------------------------------------------- 本地 CA 签发（IP 模式首选）
# IP 模式默认走本地 CA：客户端导入一次 root-ca.crt 后，443 和 8443 都不再告警。
if [ "$LOCAL_CA" = true ] || { [ "$SITE_IS_IP" = true ] && [ "$SELF_SIGNED" = false ]; }; then
  if ! ca_available; then
    if [ "$LOCAL_CA" = true ]; then
      die "本地 CA 不可用（缺 $ETC_ROOT/ca/intermediate-ca.key 等）。先执行 sudo deploy/scripts/init-ca.sh，或改用 --self-signed"
    fi
    warn "本地 CA 不可用，回退自签证书"
    SELF_SIGNED=true
  else
    STAMP=$(date +%Y%m%d-%H%M%S)
    for f in "$TLS_CERT" "$TLS_KEY"; do
      [ -f "$f" ] && cp -a "$f" "$f.bak-$STAMP"
    done
    log "用本地 CA 签发服务端证书（SAN=$TLS_SAN，825 天）"
    write_ca_signed_cert "$TLS_CERT" "$TLS_KEY" "$DOMAIN" 825 "$TLS_SAN" ||
      die "本地 CA 签发失败（检查 $ETC_ROOT/ca 下的 CA 证书与私钥是否配对）"
    chown root:root "$TLS_CERT" "$TLS_KEY"
    reload_nginx
    log "完成"
    openssl x509 -in "$TLS_CERT" -noout -subject -issuer -dates -ext subjectAltName
    cat <<EOF

链：$DOMAIN  ←  intermediate-ca.crt  ←  root-ca.crt（客户端需导入，只导一次）
客户端导入后 443 与 8443 都不再提示「不受信任」：
  Windows：certlm.msc → 受信任的根证书颁发机构 → 导入 $ETC_ROOT/ca/root-ca.crt
  或从站点的「我的证书」页面下载 root CA 后按 docs/DEPLOY.md §6 导入

EOF
    exit 0
  fi
fi

# ---------------------------------------------------------------- 自签证书
# 走到这里只有两种情况：显式 --self-signed，或 IP 模式但本地 CA 不可用
if [ "$SELF_SIGNED" = true ] || [ "$SITE_IS_IP" = true ]; then
  if [ "$SITE_IS_IP" = true ]; then
    warn "DOMAIN=$DOMAIN 是 IP，Let's Encrypt 无法为其签发证书（只签发域名）"
    info "改用自签证书（浏览器会提示不受信任）"
  fi
  STAMP=$(date +%Y%m%d-%H%M%S)
  for f in "$TLS_CERT" "$TLS_KEY"; do
    [ -f "$f" ] && cp -a "$f" "$f.bak-$STAMP"
  done
  log "签发自签证书（SAN=$TLS_SAN，397 天）"
  write_self_signed_cert "$TLS_CERT" "$TLS_KEY" "$DOMAIN" 397 "$TLS_SAN"
  chown root:root "$TLS_CERT" "$TLS_KEY"
  reload_nginx
  log "完成"
  openssl x509 -in "$TLS_CERT" -noout -subject -dates -ext subjectAltName
  cat <<EOF

自签证书只有本机信任后才能消除浏览器告警，常见做法：
  1) 直接把 $TLS_CERT 导入客户端系统/浏览器的"受信任的根证书"，
     或用 mkcert 生成一张已被本机信任的证书替换这两个文件后 nginx -s reload；
  2) 或者接受浏览器提示，点"高级 → 继续访问"（本站已关闭 HSTS，可以点进去）。
EOF
  exit 0
fi

# ------------------------------------------------------- Let's Encrypt（仅域名）
[ -n "${ACME_EMAIL:-}" ] || die "deploy.env 里 ACME_EMAIL 不能为空（Let's Encrypt 到期通知地址）"

if ! command -v certbot >/dev/null 2>&1; then
  log "安装 certbot"
  apt-get update -y
  apt-get install -y --no-install-recommends certbot
fi

install -d -m 755 "$ACME_WEBROOT"

# 续期钩子：把 live 里的证书复制到 nginx 引用路径。不要让 nginx 直接引用
# /etc/letsencrypt/live（首签前不存在，nginx 会启动失败）。
HOOK=/etc/letsencrypt/renewal-hooks/deploy/agent-platform.sh
install -d -m 755 "$(dirname "$HOOK")"
cat >"$HOOK" <<EOF
#!/bin/sh
# 由 deploy/scripts/issue-tls-cert.sh 生成
set -e
cp -f /etc/letsencrypt/live/$DOMAIN/fullchain.pem "$TLS_CERT"
cp -f /etc/letsencrypt/live/$DOMAIN/privkey.pem "$TLS_KEY"
chmod 644 "$TLS_CERT"
chmod 600 "$TLS_KEY"
nginx -t && systemctl reload nginx
EOF
chmod 755 "$HOOK"

log "检查 DNS"
resolved=$(getent ahostsv4 "$DOMAIN" | awk 'NR==1{print $1}')
info "$DOMAIN -> ${resolved:-未解析}"
[ -n "$resolved" ] || warn "域名未解析，certbot 的 HTTP 校验会失败"

log "申请证书（webroot 校验）"
args=(certonly --webroot -w "$ACME_WEBROOT" -d "$DOMAIN"
  --email "$ACME_EMAIL" --agree-tos --non-interactive --keep-until-expiring
  --deploy-hook "$HOOK")
[ "$DRY_RUN" = true ] && args+=(--dry-run)
certbot "${args[@]}"

if [ "$DRY_RUN" = true ]; then
  log "演练通过（未写入证书）"
  exit 0
fi

log "同步证书到 nginx 路径"
"$HOOK"

log "完成"
openssl x509 -in "$TLS_CERT" -noout -subject -dates
