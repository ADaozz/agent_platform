#!/usr/bin/env bash
# 生成/重建「客户端证书登录」用的一套私有 CA：Root CA + Intermediate CA。
#
#   sudo deploy/scripts/init-ca.sh                    # 首次生成
#   sudo deploy/scripts/init-ca.sh --force            # 重建（旧 CA 备份到 $ETC_ROOT/ca/backup-<时间戳>/）
#   sudo deploy/scripts/init-ca.sh --with-server-cert # 顺带重签 ca/server/personal-demo 的本地服务端证书
#
# 产物（私钥只落 /etc，绝不入库；公钥证书写回仓库 ca/，供 install-host.sh 与用户 bundle 使用）：
#   $ETC_ROOT/ca/                            750 root:<服务用户> —— 必须可穿越，否则后端读不到 key
#   $ETC_ROOT/ca/root-ca.key                 600 root:root      —— 只在重签 intermediate 时用，离线保存
#   $ETC_ROOT/ca/intermediate-ca.key         640 root:<服务用户> —— 后端签用户证书要用（必须可读）
#   $ETC_ROOT/ca/root-ca.crt                 644
#   $ETC_ROOT/ca/intermediate-ca.crt         644
#   <仓库>/ca/root/root-ca.crt               644（公开证书，入库）
#   <仓库>/ca/intermediate/intermediate-ca.crt 644（公开证书，入库）
#
# 生成后还要做两件事（脚本会提示）：
#   1. 把 root-ca.crt 导入浏览器/系统的「受信任的根证书颁发机构」；
#   2. deploy.env 里 CERT_LOGIN_ENABLED=true 后重跑 install-host.sh，才会监听 8443。
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"

require_root
load_env
require_cmd openssl

FORCE=false
WITH_SERVER=false
usage() {
  cat <<'EOF'
用法：sudo deploy/scripts/init-ca.sh [选项]

  --force             已有 CA 时先备份再重建（默认拒绝，避免把已签发的证书全部作废）
  --with-server-cert  顺带用新 CA 重签 ca/server/personal-demo 的本地服务端证书
  -h, --help          显示本帮助

可用环境变量（也可写进 deploy.env）：
  CA_ORG / CA_EMAIL / CA_ROOT_CN / CA_INTERMEDIATE_CN
  DAYS_ROOT / DAYS_INTERMEDIATE / DAYS_SERVER
  CA_PUBLIC_DIR      公钥证书写回目录，默认 <仓库>/ca
EOF
}
while [ $# -gt 0 ]; do
  case "$1" in
    --force) FORCE=true ;;
    --with-server-cert) WITH_SERVER=true ;;
    -h | --help) usage; exit 0 ;;
    *) die "未知参数：$1（--help 看用法）" ;;
  esac
  shift
done

# ---- 参数（默认值与仓库现有 CA 保持一致，Chrome 自动选证 .reg 依赖中间 CA 的 CN）----
CA_ORG=${CA_ORG:-personalDemo}
CA_EMAIL=${CA_EMAIL:-ca@example.com}
CA_ROOT_CN=${CA_ROOT_CN:-Root CA}
CA_INTERMEDIATE_CN=${CA_INTERMEDIATE_CN:-personalDemo Intermediate CA}
DAYS_ROOT=${DAYS_ROOT:-3650}
DAYS_INTERMEDIATE=${DAYS_INTERMEDIATE:-1825}
DAYS_SERVER=${DAYS_SERVER:-825}
CA_PUBLIC_DIR=${CA_PUBLIC_DIR:-$REPO_ROOT/ca}

CA_DIR=$ETC_ROOT/ca
KEY_BITS=${KEY_BITS:-4096}
STAMP=$(date +%Y%m%d-%H%M%S)

subj_root="/C=CN/ST=Shanghai/L=Shanghai/O=$CA_ORG/OU=Security/CN=$CA_ROOT_CN/emailAddress=$CA_EMAIL"
subj_intermediate="/C=CN/ST=Shanghai/L=Shanghai/O=$CA_ORG/OU=Security/CN=$CA_INTERMEDIATE_CN/emailAddress=$CA_EMAIL"
subj_server="/C=CN/ST=Shanghai/L=Shanghai/O=$CA_ORG/OU=Web/CN=localhost"

# --------------------------------------------------------------- 0. 冲突检查
# 目录必须让服务用户可穿越：intermediate-ca.key 是 640 root:<SERVICE_USER>，
# 若目录仍是 700 root:root，后端会报「中间 CA 文件不存在」而无法签发。
install -d -m 750 "$CA_DIR"
if id -u "$SERVICE_USER" >/dev/null 2>&1; then
  chown "root:$SERVICE_USER" "$CA_DIR"
fi
if [ -f "$CA_DIR/root-ca.key" ] || [ -f "$CA_DIR/intermediate-ca.key" ]; then
  if [ "$FORCE" != true ]; then
    die "$CA_DIR 已有 CA 私钥。重建会让所有已签发的客户端证书失效，
       确认要换 CA 就加 --force（旧材料会先备份到 $CA_DIR/backup-$STAMP/）"
  fi
  log "0/4 备份旧 CA 到 $CA_DIR/backup-$STAMP"
  install -d -m 700 "$CA_DIR/backup-$STAMP"
  for f in "$CA_DIR"/*.key "$CA_DIR"/*.crt; do
    [ -f "$f" ] && cp -a "$f" "$CA_DIR/backup-$STAMP/"
  done
  info "已备份 $(ls -1 "$CA_DIR/backup-$STAMP" | wc -l) 个文件"
fi

# ------------------------------------------------------------- 1. 根 CA
log "1/4 生成根 CA：$CA_ROOT_CN（$DAYS_ROOT 天，RSA $KEY_BITS）"
umask 077
openssl genrsa -out "$CA_DIR/root-ca.key" "$KEY_BITS" 2>/dev/null
openssl req -x509 -new -key "$CA_DIR/root-ca.key" -sha256 -days "$DAYS_ROOT" -subj "$subj_root" \
  -addext "basicConstraints=critical,CA:TRUE,pathlen:1" \
  -addext "keyUsage=critical,keyCertSign,cRLSign" \
  -addext "subjectKeyIdentifier=hash" \
  -out "$CA_DIR/root-ca.crt"
chmod 600 "$CA_DIR/root-ca.key"
chmod 644 "$CA_DIR/root-ca.crt"
info "自签名：$(openssl x509 -in "$CA_DIR/root-ca.crt" -noout -subject)"
info "有效期：$(openssl x509 -in "$CA_DIR/root-ca.crt" -noout -enddate | cut -d= -f2)"

# --------------------------------------------------------- 2. 中间 CA
log "2/4 生成中间 CA：$CA_INTERMEDIATE_CN（$DAYS_INTERMEDIATE 天，由根 CA 签）"
CSR=$CA_DIR/intermediate-ca.csr
openssl genrsa -out "$CA_DIR/intermediate-ca.key" "$KEY_BITS" 2>/dev/null
openssl req -new -key "$CA_DIR/intermediate-ca.key" -subj "$subj_intermediate" -out "$CSR"
# 用仓库里的扩展配置：pathlen:0 → 中间 CA 只能签终端证书，不能再签下级 CA
openssl x509 -req -in "$CSR" -sha256 -days "$DAYS_INTERMEDIATE" \
  -CA "$CA_DIR/root-ca.crt" -CAkey "$CA_DIR/root-ca.key" \
  -set_serial "0x$(openssl rand -hex 16)" \
  -extfile "$REPO_ROOT/ca/intermediate/intermediate-ca.ext" \
  -out "$CA_DIR/intermediate-ca.crt"
rm -f "$CSR"
chmod 644 "$CA_DIR/intermediate-ca.crt"
# 后端以服务用户身份读私钥签发证书，必须可读；root 私钥只给 root
chmod 600 "$CA_DIR/root-ca.key"
if id -u "$SERVICE_USER" >/dev/null 2>&1; then
  chown "root:$SERVICE_USER" "$CA_DIR/intermediate-ca.key"
  chmod 640 "$CA_DIR/intermediate-ca.key"
else
  # 还没跑 install-host.sh 时系统用户不存在；install-host.sh 会补上属主
  warn "系统用户 $SERVICE_USER 不存在，intermediate-ca.key 暂为 root:root 600"
  warn "跑完 sudo deploy/scripts/install-host.sh 后它会自动 chown 到 root:$SERVICE_USER"
  chmod 600 "$CA_DIR/intermediate-ca.key"
fi
chown root:root "$CA_DIR/root-ca.crt" "$CA_DIR/intermediate-ca.crt"

# ------------------------------------------------------------ 3. 自检
log "3/4 校验证书链"
openssl verify -CAfile "$CA_DIR/root-ca.crt" "$CA_DIR/intermediate-ca.crt"
issuer=$(openssl x509 -in "$CA_DIR/intermediate-ca.crt" -noout -issuer | sed 's/^issuer=//')
root_subject=$(openssl x509 -in "$CA_DIR/root-ca.crt" -noout -subject | sed 's/^subject=//')
[ "$issuer" = "$root_subject" ] || die "中间 CA 的 issuer 与根 CA 的 subject 不一致：$issuer vs $root_subject"
info "中间 CA issuer 与根 CA subject 一致"
info "中间 CA 私钥权限：$(stat -c '%a %U:%G' "$CA_DIR/intermediate-ca.key")"

# ------------------------------------------------- 4. 公钥回写仓库 + 可选服务端证书
log "4/4 写回公钥证书到 $CA_PUBLIC_DIR"
install -d -m 755 "$CA_PUBLIC_DIR/root" "$CA_PUBLIC_DIR/intermediate"
install -m 644 "$CA_DIR/root-ca.crt" "$CA_PUBLIC_DIR/root/root-ca.crt"
install -m 644 "$CA_DIR/intermediate-ca.crt" "$CA_PUBLIC_DIR/intermediate/intermediate-ca.crt"
info "$CA_PUBLIC_DIR/root/root-ca.crt"
info "$CA_PUBLIC_DIR/intermediate/intermediate-ca.crt"

if [ "$WITH_SERVER" = true ]; then
  log "附加：重签本地服务端证书（CN=localhost）"
  SRV_DIR=$CA_PUBLIC_DIR/server/personal-demo
  install -d -m 755 "$SRV_DIR"
  install -d -m 700 "$CA_DIR/server"
  openssl genrsa -out "$CA_DIR/server/server.key" 2048 2>/dev/null
  openssl req -new -key "$CA_DIR/server/server.key" -subj "$subj_server" -out "$CA_DIR/server/server.csr"
  openssl x509 -req -in "$CA_DIR/server/server.csr" -sha256 -days "$DAYS_SERVER" \
    -CA "$CA_DIR/intermediate-ca.crt" -CAkey "$CA_DIR/intermediate-ca.key" \
    -set_serial "0x$(openssl rand -hex 16)" \
    -extfile "$REPO_ROOT/ca/server/personal-demo/server.ext" \
    -out "$SRV_DIR/server.crt"
  cat "$SRV_DIR/server.crt" "$CA_DIR/intermediate-ca.crt" "$CA_DIR/root-ca.crt" >"$SRV_DIR/server-chain.crt"
  rm -f "$CA_DIR/server/server.csr"
  chmod 644 "$SRV_DIR/server.crt" "$SRV_DIR/server-chain.crt"
  chmod 600 "$CA_DIR/server/server.key"
  info "私钥：$CA_DIR/server/server.key（600，不入库）"
  info "证书：$SRV_DIR/server.crt + server-chain.crt"
fi

# --------------------------------------------------------------- 收尾
umask 022
root_fp=$(openssl x509 -in "$CA_DIR/root-ca.crt" -noout -fingerprint -sha256 | sed 's/^.*=//')
int_fp=$(openssl x509 -in "$CA_DIR/intermediate-ca.crt" -noout -fingerprint -sha256 | sed 's/^.*=//')

log "完成"
cat <<EOF

根 CA 指纹（SHA256）：$root_fp
中间 CA 指纹（SHA256）：$int_fp

接下来必须做的事：
  1. 把 $CA_DIR/root-ca.crt 导入客户端的「受信任的根证书颁发机构」
     （Windows：certlm.msc → 受信任的根证书颁发机构 → 导入；或「我的证书」页面下载 bundle 后按文档导入）
  2. 备份 $CA_DIR/intermediate-ca.key 与 $CA_DIR/root-ca.key 到离线介质：
     丢了 intermediate-ca.key 就再也签不出新的客户端证书（只能再来一次 init-ca.sh）；
     丢了 root-ca.key 就无法重签 intermediate（10 年后根 CA 到期时会很麻烦）。
  3. 想启用 8443 证书登录：deploy.env 里 CERT_LOGIN_ENABLED=true，然后重跑
     sudo deploy/scripts/install-host.sh
  4. 已签发的旧客户端证书（如果之前用过）全部失效，需要重新申请。

EOF
