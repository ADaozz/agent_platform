#!/usr/bin/env bash
# 目标机首次安装：装包、建用户与目录、生成密钥、安装 redis / nginx / systemd 配置。
# 幂等：可以反复执行；已存在的 secrets.env 与证书不会被覆盖。
#
#   sudo deploy/scripts/install-host.sh
#
# 前置：/etc/agent-platform/deploy.env 已按 deploy.env.example 填好。
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"

require_root
load_env
require_cmd openssl
export DEBIAN_FRONTEND=noninteractive

# 每步打印已用时间，卡在哪一步一眼能看出来（首次装 LibreOffice 可能要十几分钟）
T0=$(date +%s)
elapsed() { local s=$(($(date +%s) - T0)); printf '%dm%02ds' $((s / 60)) $((s % 60)); }
log() { printf '\n\033[1;34m==> [%s] %s\033[0m\n' "$(elapsed)" "$*"; }
info() { printf '    %s\n' "$*"; }

# 三个服务都由 systemd 单元托管；WSL2 默认可能没开
if [ "$(ps -p 1 -o comm= 2>/dev/null)" != "systemd" ]; then
  die "PID 1 不是 systemd。WSL2 请在 /etc/wsl.conf 写入 '[boot]' + 'systemd=true'，再执行 wsl --shutdown 重开；或改用非 systemd 方式部署"
fi

DB_FILE="$DATA_ROOT/data/agent-platform.db"

# ---------------------------------------------------------------- 1. 软件包
log "1/8 安装系统软件包"

# 国内网络下 archive.ubuntu.com 实测只有 ~85 KB/s（清华镜像 ~900 KB/s，大包差距更大），
# LibreOffice 410MB 按这个速度要一个多小时。所以默认把官方源换成镜像。
#   APT_MIRROR=           关闭自动换源（保留现有 sources.list）
#   APT_MIRROR=<url>      指定别的镜像，例如 https://mirrors.aliyun.com/ubuntu
#   APT_PROXY=<url>       apt 走代理，例如 http://172.27.224.1:12450
APT_MIRROR=${APT_MIRROR-https://mirrors.tuna.tsinghua.edu.cn/ubuntu}
APT_PROXY=${APT_PROXY:-}
apt_opts=()
if [ -n "$APT_PROXY" ]; then
  apt_opts+=(-o "Acquire::http::Proxy=$APT_PROXY" -o "Acquire::https::Proxy=$APT_PROXY")
  info "apt 走代理 $APT_PROXY"
fi
if [ -n "$APT_MIRROR" ] && ! printf '%s' "$APT_MIRROR" | grep -qE '^https?://[^ #&]+$'; then
  warn "APT_MIRROR 格式不对（$APT_MIRROR），跳过换源"
  APT_MIRROR=
fi
if [ -n "$APT_MIRROR" ] && [ -f /etc/apt/sources.list ] &&
  grep -qE 'https?://(archive|security)\.ubuntu\.com/ubuntu' /etc/apt/sources.list; then
  [ -f /etc/apt/sources.list.agent-platform.bak ] || cp -a /etc/apt/sources.list /etc/apt/sources.list.agent-platform.bak
  sed -i -E "s#https?://(archive|security)\.ubuntu\.com/ubuntu#${APT_MIRROR}#g" /etc/apt/sources.list
  info "apt 源已切到 $APT_MIRROR（原文件：/etc/apt/sources.list.agent-platform.bak）"
fi

# 已装齐就不碰 apt：重跑安装时能省掉 update + 索引下载
missing=""
for p in nginx redis-server sqlite3 ca-certificates curl openssl gettext-base \
  openjdk-8-jre-headless ufw bubblewrap build-essential libsqlite3-dev rsync python3-bcrypt; do
  dpkg -s "$p" >/dev/null 2>&1 || missing="$missing $p"
done
if [ -z "$missing" ]; then
  info "系统软件包已齐全，跳过 apt"
else
  info "待安装：$missing"
  apt-get "${apt_opts[@]}" update -y
  # shellcheck disable=SC2086
  apt-get "${apt_opts[@]}" install -y --no-install-recommends $missing
fi

if ! command -v python3.12 >/dev/null 2>&1; then
  log "安装 Python 3.12"
  apt-get "${apt_opts[@]}" install -y --no-install-recommends software-properties-common
  add-apt-repository -y universe >/dev/null
  add-apt-repository -y ppa:deadsnakes/ppa >/dev/null
  apt-get "${apt_opts[@]}" update -y
  apt-get "${apt_opts[@]}" install -y --no-install-recommends python3.12 python3.12-venv python3.12-dev
fi

if [ "${INSTALL_OFFICE:-false}" = true ]; then
  if command -v libreoffice >/dev/null 2>&1; then
    info "LibreOffice 已安装，跳过（约 410MB，是首次安装里最慢的一步）"
  else
    log "安装 LibreOffice 与中文字体（约 410MB，首次会久）"
    apt-get "${apt_opts[@]}" install -y --no-install-recommends \
      libreoffice-writer libreoffice-impress libreoffice-core fonts-noto-cjk
  fi
fi

if [ "${INSTALL_BUILD_TOOLS:-false}" = true ]; then
  log "安装 JDK 与 Maven（可选，用于在本机构建）"
  # 构建用 JDK 8：pom 的 source/target 为 1.8，Lombok（Boot 2.6 BOM = 1.18.24）
  # 不支持 JDK 21+，运行时也用同一版本最稳
  apt-get "${apt_opts[@]}" install -y --no-install-recommends openjdk-8-jdk maven
fi

# ------------------------------------------------------------ 2. 用户与目录
log "2/8 创建服务用户与目录"
if ! id -u "$SERVICE_USER" >/dev/null 2>&1; then
  useradd --system --home-dir "$DATA_ROOT" --shell /usr/sbin/nologin "$SERVICE_USER"
  info "已创建用户 $SERVICE_USER"
fi
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 750 "$DATA_ROOT"
# 代码目录用 755：nginx 以 www-data 身份读 current/frontend 下的静态资源，
# 750 会让 www-data 连穿越都做不到，页面全 404（API 反而正常，很难察觉）。
# 这里只有发布产物，没有密钥，静态资源本来就要公开给 web 服务器读。
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 755 "$APP_ROOT" "$APP_ROOT/releases"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 750 \
  "$DATA_ROOT/data" "$DATA_ROOT/certs" "$DATA_ROOT/runtime" "$DATA_ROOT/runtime/tmp"
install -d -m 755 "$ETC_ROOT"

# 把 deploy/ 留在服务器上，后续 release / backup / healthcheck 直接复用
if [ "$REPO_ROOT/deploy" != "$APP_ROOT/deploy" ]; then
  rsync -a --delete "$REPO_ROOT/deploy/" "$APP_ROOT/deploy/"
  chown -R root:root "$APP_ROOT/deploy"
fi

# --------------------------------------------------------------- 3. 密钥
log "3/8 生成服务密钥（已存在则复用）"
if [ ! -f "$ETC_ROOT/secrets.env" ]; then
  shared=$(gen_secret)
  umask 077
  cat >"$ETC_ROOT/secrets.env" <<EOF
# 由 deploy/scripts/install-host.sh 生成，勿入库、勿丢失。
# backend 与 runtime 必须使用同一个 AGENT_RUNTIME_SHARED_SECRET / ITAM_RUNTIME_SHARED_SECRET。
JWT_SECRET=$(gen_secret)
JWT_API_SECRET=$(gen_secret)
AGENT_RUNTIME_SHARED_SECRET=$shared
ITAM_RUNTIME_SHARED_SECRET=$shared
REDIS_PASSWORD=$(gen_secret)
# 注册验证码发件账号（163 邮箱填授权码）；不需要自助注册可以留空
MAIL_USERNAME=${MAIL_USERNAME:-}
MAIL_PASSWORD=${MAIL_PASSWORD:-}
EOF
  umask 022
  info "已写入 $ETC_ROOT/secrets.env"
else
  info "复用已有 $ETC_ROOT/secrets.env"
  # deploy.env 里补填了邮件账号时同步过去（幂等，空值不覆盖）
  if [ -n "${MAIL_USERNAME:-}" ] && [ "$(secret_get "$ETC_ROOT/secrets.env" MAIL_USERNAME)" != "$MAIL_USERNAME" ]; then
    secret_set "$ETC_ROOT/secrets.env" MAIL_USERNAME "$MAIL_USERNAME"
    info "已更新 secrets.env 的 MAIL_USERNAME"
  fi
  if [ -n "${MAIL_PASSWORD:-}" ] && [ "$(secret_get "$ETC_ROOT/secrets.env" MAIL_PASSWORD)" != "$MAIL_PASSWORD" ]; then
    secret_set "$ETC_ROOT/secrets.env" MAIL_PASSWORD "$MAIL_PASSWORD"
    info "已更新 secrets.env 的 MAIL_PASSWORD"
  fi
fi
chown "root:$SERVICE_USER" "$ETC_ROOT/secrets.env"
chmod 640 "$ETC_ROOT/secrets.env"
REDIS_PASSWORD=$(secret_get "$ETC_ROOT/secrets.env" REDIS_PASSWORD)
[ -n "$REDIS_PASSWORD" ] || die "$ETC_ROOT/secrets.env 缺少 REDIS_PASSWORD"
# render 用 envsubst，只认环境变量：不 export 就会渲染成空密码
export REDIS_PASSWORD

# --------------------------------------------------------- 4. SQLite 数据文件
log "4/8 初始化 SQLite 数据文件"
if [ ! -f "$DB_FILE" ]; then
  # journal_mode=WAL 是写进库文件的持久属性，建表交给后端启动时的 spring.sql.init
  install -o "$SERVICE_USER" -g "$SERVICE_USER" -m 640 /dev/null "$DB_FILE"
  sqlite3 "$DB_FILE" 'PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;' >/dev/null
  info "已创建 $DB_FILE（WAL）"
else
  info "已存在 $DB_FILE，跳过"
fi

# ---------------------------------------------------------------- 5. Redis
log "5/8 配置 Redis"
install -d -o redis -g redis -m 750 "$REDIS_DATA_DIR" "$REDIS_LOG_DIR"
install -d -m 755 "$(dirname "$REDIS_CONF")"
render "$REPO_ROOT/deploy/redis/agent-platform.conf.template" "$REDIS_CONF" 640 \
  REDIS_PORT REDIS_PASSWORD REDIS_DATA_DIR REDIS_LOG_DIR
chown root:redis "$REDIS_CONF"

# 发行版自带的实例监听同一个 6379，必须让位给我们的配置（AOF + 密码 + noeviction）
systemctl disable --now redis-server.service >/dev/null 2>&1 || true
systemctl mask redis-server.service >/dev/null 2>&1 || true

render "$REPO_ROOT/deploy/systemd/redis-agent-platform.service.template" \
  /etc/systemd/system/redis-agent-platform.service 644 \
  REDIS_CONF REDIS_DATA_DIR REDIS_LOG_DIR
systemctl daemon-reload
systemctl enable redis-agent-platform.service >/dev/null
systemctl restart redis-agent-platform.service
sleep 1
if ! REDISCLI_AUTH="$REDIS_PASSWORD" redis-cli -h 127.0.0.1 -p "$REDIS_PORT" ping 2>/dev/null | grep -q PONG; then
  journalctl -u redis-agent-platform.service -n 30 --no-pager >&2 || true
  die "Redis 启动失败"
fi
info "Redis 正常（127.0.0.1:$REDIS_PORT，AOF，noeviction）"

# ------------------------------------------------------- 6. CA 与 TLS 证书
log "6/8 准备 CA 与 TLS 证书"
if [ "$CERT_LOGIN_ENABLED" = true ] || [ -n "${CA_SOURCE_DIR:-}" ]; then
  # 750 + group=$SERVICE_USER：后端要读 intermediate-ca.key；700 会让 Java 误报「文件不存在」
  install -d -m 750 "$ETC_ROOT/ca"
  chown "root:$SERVICE_USER" "$ETC_ROOT/ca"
  ca_src=${CA_SOURCE_DIR:-}
  if [ -z "$ca_src" ] && [ -f "$REPO_ROOT/ca/root/root-ca.crt" ]; then
    ca_src="$REPO_ROOT/ca"
  fi
  if [ -n "$ca_src" ] && [ -d "$ca_src" ]; then
    # 只在 /etc 缺文件时补：/etc 是运行中的权威副本，用仓库里可能过期的公钥覆盖它，
    # 会让 intermediate-ca.key 与 intermediate-ca.crt 不再配对（申请证书全失败）。
    copied=false
    if [ ! -f "$ETC_ROOT/ca/root-ca.crt" ] && [ -f "$ca_src/root/root-ca.crt" ]; then
      install -m 644 "$ca_src/root/root-ca.crt" "$ETC_ROOT/ca/root-ca.crt"
      copied=true
    fi
    if [ ! -f "$ETC_ROOT/ca/intermediate-ca.crt" ] && [ -f "$ca_src/intermediate/intermediate-ca.crt" ]; then
      install -m 644 "$ca_src/intermediate/intermediate-ca.crt" "$ETC_ROOT/ca/intermediate-ca.crt"
      copied=true
    fi
    if [ ! -f "$ETC_ROOT/ca/intermediate-ca.key" ] && [ -f "$ca_src/intermediate/intermediate-ca.key" ]; then
      install -m 600 "$ca_src/intermediate/intermediate-ca.key" "$ETC_ROOT/ca/intermediate-ca.key"
      copied=true
    fi
    [ "$copied" = true ] && info "CA 材料已从 $ca_src 补齐" || info "保留 $ETC_ROOT/ca 现有 CA 材料"
  fi
  if [ ! -f "$ETC_ROOT/ca/intermediate-ca.key" ]; then
    warn "缺少 $ETC_ROOT/ca/intermediate-ca.key：现有证书还能验证，但页面「申请证书」会失败"
    warn "  生成一套带私钥的 CA：sudo deploy/scripts/init-ca.sh（详见 docs/DEPLOY.md §6.1）"
  fi
  # 每次覆盖重建：换 CA（如 init-ca.sh --force）后旧 bundle 残留会让所有客户端证书验链失败
  if [ -s "$ETC_ROOT/ca/intermediate-ca.crt" ] && [ -s "$ETC_ROOT/ca/root-ca.crt" ]; then
    install -d -m 700 "$(dirname "$TLS_CLIENT_CA")"
    cat "$ETC_ROOT/ca/intermediate-ca.crt" "$ETC_ROOT/ca/root-ca.crt" >"$TLS_CLIENT_CA" ||
      die "无法生成客户端 CA bundle（$TLS_CLIENT_CA）"
    chmod 644 "$TLS_CLIENT_CA"
    info "已生成客户端 CA bundle：$TLS_CLIENT_CA"
  elif [ ! -s "$TLS_CLIENT_CA" ]; then
    die "缺少 CA 证书（$ETC_ROOT/ca/intermediate-ca.crt），无法生成客户端 CA bundle"
  fi
fi

# init-ca.sh 可能早于本脚本执行（那时服务用户还不存在），这里幂等补齐属主与目录穿越权限
if [ -d "$ETC_ROOT/ca" ]; then
  chown "root:$SERVICE_USER" "$ETC_ROOT/ca"
  chmod 750 "$ETC_ROOT/ca"
fi
if [ -f "$ETC_ROOT/ca/intermediate-ca.key" ]; then
  chown "root:$SERVICE_USER" "$ETC_ROOT/ca/intermediate-ca.key"
  chmod 640 "$ETC_ROOT/ca/intermediate-ca.key"
fi

if [ ! -s "$TLS_CERT" ] || [ ! -s "$TLS_KEY" ]; then
  # 优先用本地 CA 签：客户端导入一次 root-ca.crt 后，443 和 8443 的信任一起解决，
  # 不会出现「8443 能登录但 443 一直弹安全警告」的割裂感。CA 不可用时回退自签。
  if write_ca_signed_cert "$TLS_CERT" "$TLS_KEY" "$DOMAIN" 825 "$TLS_SAN"; then
    info "已用本地 CA 签发服务端证书：$TLS_CERT（客户端需导入 ca/root/root-ca.crt 才不告警）"
  else
    write_self_signed_cert "$TLS_CERT" "$TLS_KEY" "$DOMAIN" 397 "$TLS_SAN"
    if [ "$SITE_IS_IP" = true ]; then
      warn "已为 IP $DOMAIN 生成自签证书（397 天）：浏览器会提示「不受信任」，需要手动信任或继续访问；"
      warn "IP 无法用 Let's Encrypt 签证书；先跑 deploy/scripts/init-ca.sh 可改用本地 CA 签发（导入一次即无告警）"
    else
      warn "已生成自签占位证书；正式对外前执行 deploy/scripts/issue-tls-cert.sh 换成受信任证书"
    fi
  fi
fi

# ---------------------------------------------------------------- 7. Nginx
log "7/8 配置 Nginx"
install -d -m 755 "$ACME_WEBROOT"
rm -f /etc/nginx/sites-enabled/default

render "$REPO_ROOT/deploy/nginx/agent-platform.conf.template" \
  /etc/nginx/sites-available/agent-platform.conf 644 \
  DOMAIN TLS_CERT TLS_KEY TLS_CLIENT_CA WEB_ROOT BACKEND_ADDR ACME_WEBROOT HSTS_HEADER

if [ "$CERT_LOGIN_ENABLED" = true ]; then
  render "$REPO_ROOT/deploy/nginx/cert-login-8443.conf.template" \
    /etc/nginx/snippets/agent-platform-cert-login.conf 644 \
    DOMAIN TLS_CERT TLS_KEY TLS_CLIENT_CA BACKEND_ADDR HSTS_HEADER
else
  printf '# 客户端证书登录未启用（CERT_LOGIN_ENABLED=false），8443 不监听\n' \
    >/etc/nginx/snippets/agent-platform-cert-login.conf
fi
ln -sfn /etc/nginx/sites-available/agent-platform.conf /etc/nginx/sites-enabled/agent-platform.conf

if ! nginx -t; then
  die "Nginx 配置检查失败，未重载"
fi
systemctl enable nginx >/dev/null
systemctl reload nginx 2>/dev/null || systemctl restart nginx
info "Nginx 已加载 https://$DOMAIN"

# ------------------------------------------------------------ 8. systemd 与防火墙
log "8/8 安装后端 / Runtime 服务单元"
render "$REPO_ROOT/deploy/systemd/agent-platform-backend.service.template" \
  /etc/systemd/system/agent-platform-backend.service 644 \
  SERVICE_USER APP_ROOT DATA_ROOT ETC_ROOT BACKEND_PORT
render "$REPO_ROOT/deploy/systemd/agent-platform-runtime.service.template" \
  /etc/systemd/system/agent-platform-runtime.service 644 \
  SERVICE_USER APP_ROOT DATA_ROOT ETC_ROOT RUNTIME_PORT
render "$REPO_ROOT/deploy/env/backend.env.template" "$ETC_ROOT/backend.env" 640 \
  DOMAIN DATA_ROOT ETC_ROOT BACKEND_PORT RUNTIME_PORT REDIS_PORT CERT_LOGIN_ENABLED
render "$REPO_ROOT/deploy/env/runtime.env.template" "$ETC_ROOT/runtime.env" 640 \
  DATA_ROOT ETC_ROOT

chown root:"$SERVICE_USER" "$ETC_ROOT/backend.env" "$ETC_ROOT/runtime.env"
systemctl daemon-reload
systemctl enable agent-platform-backend.service agent-platform-runtime.service >/dev/null

# bwrap 需要非特权 user namespace
if [ "$(sysctl -n kernel.unprivileged_userns_clone 2>/dev/null || echo 1)" = "0" ]; then
  echo 'kernel.unprivileged_userns_clone=1' >/etc/sysctl.d/90-agent-platform.conf
  sysctl --system >/dev/null
  info "已启用 kernel.unprivileged_userns_clone"
fi

if command -v ufw >/dev/null 2>&1; then
  # 只放行真正需要对外的那一个入口：nginx 的 443（域名模式再加 80 给 ACME 用）。
  # 8080/8090/6379 绑在回环上，不要单独放行——明文 HTTP 会绕过 TLS 与 nginx 的安全头。
  # WSL2 里常缺 netfilter 模块，ufw 可能起不来；那不是致命问题（真正的边界在 Windows 防火墙），
  # 所以这里失败只告警，不中断安装。
  FW_PORTS="22/tcp 443/tcp"
  [ "$SITE_IS_IP" = true ] || FW_PORTS="22/tcp 80/tcp 443/tcp"
  [ "$CERT_LOGIN_ENABLED" = true ] && FW_PORTS="$FW_PORTS 8443/tcp"
  fw_ok=true
  for p in $FW_PORTS; do
    ufw allow "$p" >/dev/null 2>&1 || fw_ok=false
  done
  if [ "$fw_ok" = true ] && ufw --force enable >/dev/null 2>&1; then
    info "ufw 已启用：$FW_PORTS"
  else
    warn "ufw 启用失败（WSL2 常见）：请改为在 Windows 防火墙与路由器上限制入站，见 docs/DEPLOY.md §WSL2"
  fi
fi

if [ -L "$APP_ROOT/current" ]; then
  systemctl restart agent-platform-backend.service agent-platform-runtime.service
else
  info "尚未发布版本（$APP_ROOT/current 不存在），装完可直接跑 deploy/scripts/release.sh"
fi

log "安装完成（总耗时 $(elapsed)）"
if [ "$SITE_IS_IP" = true ]; then
  cat <<EOF

注意：DOMAIN=$DOMAIN 是 IP，只能用自签证书访问 https://$DOMAIN/
      - 浏览器首次访问会提示证书不受信任，点「高级 → 继续访问」即可（已自动关闭 HSTS）
      - 想换证书：sudo deploy/scripts/issue-tls-cert.sh --self-signed

接下来：
  1. 邮件账号已写入 $ETC_ROOT/secrets.env（需要改：sudo vi $ETC_ROOT/secrets.env）
  2. 首次发布：  sudo $APP_ROOT/deploy/scripts/release.sh <发布目录>
  3. 健康检查：  sudo $APP_ROOT/deploy/scripts/healthcheck.sh
  4. 唯一管理员：sudo $APP_ROOT/deploy/scripts/set-admin.sh（删掉内置 admin，只留 ADMIN_USERNAME）
  见 docs/DEPLOY.md §5

EOF
else
  cat <<EOF

接下来：
  1. 填写邮件账号（自助注册用）：sudo vi $ETC_ROOT/secrets.env
  2. 签发正式证书：           sudo deploy/scripts/issue-tls-cert.sh
  3. 首次发布：               sudo $APP_ROOT/deploy/scripts/release.sh <发布目录>
  4. 健康检查：               sudo $APP_ROOT/deploy/scripts/healthcheck.sh
  5. 唯一管理员：             sudo $APP_ROOT/deploy/scripts/set-admin.sh（删掉内置 admin，只留 ADMIN_USERNAME）
  见 docs/DEPLOY.md §5

EOF
fi
