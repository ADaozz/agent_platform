#!/usr/bin/env bash
# 发布/回滚：把构建产物切到 $APP_ROOT/current 并重启服务。
#
#   sudo deploy/scripts/release.sh <发布目录>            # 目录里有 backend.jar / frontend / runtime
#   sudo deploy/scripts/release.sh --update-runtime-deps <发布目录>
#
# 失败会自动切回上一个版本并重启，退出码非 0。
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"

require_root
load_env

UPDATE_DEPS=false
if [ "${1:-}" = "--update-runtime-deps" ]; then
  UPDATE_DEPS=true
  shift
fi
SRC=${1:-}
[ -n "$SRC" ] || die "用法：release.sh [--update-runtime-deps] <发布目录>"
[ -d "$SRC" ] || die "发布目录不存在：$SRC"
[ -f "$SRC/backend.jar" ] || die "$SRC 缺少 backend.jar"
[ -f "$SRC/frontend/index.html" ] || die "$SRC 缺少 frontend/index.html"
[ -f "$SRC/runtime/platform_app/main.py" ] || die "$SRC 缺少 runtime/platform_app/main.py"

VERSION=$(sed -n 's/^version=//p' "$SRC/RELEASE" 2>/dev/null | head -1)
VERSION=${VERSION:-$(basename "$(cd "$SRC" && pwd)")}
TARGET="$APP_ROOT/releases/$VERSION"
PREVIOUS=$(readlink -f "$APP_ROOT/current" 2>/dev/null || true)

log "发布 $VERSION"
info "来源：$SRC"
info "目标：$TARGET"

# 1. 同步代码 ---------------------------------------------------------------
# releases 用 755：nginx（www-data）要穿越到 current/frontend，750 会让静态资源全 404
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 755 "$APP_ROOT/releases"
rsync -a --delete "$SRC/" "$TARGET/"
chown -R "$SERVICE_USER:$SERVICE_USER" "$TARGET"
# o+rX：目录补 +x、文件补 +r（不改变可执行位），保证 www-data 能读前端
chmod -R o+rX "$TARGET"

# 2. Python 运行时依赖 ------------------------------------------------------
# 核心 lock 仅在首次或显式 UPDATE_DEPS 时重装；DOCX/PPTX 预览依赖很小，
# 每次发布都核对，避免“venv 已存在但缺 lxml/python-pptx → 预览面板不挂载”。
if [ ! -x "$APP_ROOT/venv/bin/uvicorn" ] || [ "$UPDATE_DEPS" = true ]; then
  log "安装 Python 运行时依赖（首次较慢，3-10 分钟）"
  if [ ! -x "$APP_ROOT/venv/bin/python" ]; then
    python3.12 -m venv "$APP_ROOT/venv"
  fi
  "$APP_ROOT/venv/bin/pip" install --upgrade pip wheel >/dev/null
  "$APP_ROOT/venv/bin/pip" install -r "$TARGET/runtime/requirements.lock"
fi
feature_reqs=()
for req in \
  "$TARGET/runtime/docx-ooxml-skill/requirements.txt" \
  "$TARGET/runtime/pptx-ooxml-skill/requirements.txt"
do
  [ -f "$req" ] && feature_reqs+=(-r "$req")
done
if [ "${#feature_reqs[@]}" -gt 0 ]; then
  log "安装 / 核对 Office 预览依赖（lxml、python-pptx 等）"
  "$APP_ROOT/venv/bin/pip" install "${feature_reqs[@]}"
fi
chown -R "$SERVICE_USER:$SERVICE_USER" "$APP_ROOT/venv"

# 3. 切换并重启 -------------------------------------------------------------
log "切换 current -> $VERSION"
ln -sfn "$TARGET" "$APP_ROOT/current"

systemctl restart agent-platform-runtime.service
systemctl restart agent-platform-backend.service

# 4. 健康检查，失败自动回滚 -------------------------------------------------
log "等待服务就绪（最多 120 秒）"
ok=false
for _ in $(seq 1 60); do
  if "$HERE/healthcheck.sh" --quiet >/dev/null 2>&1; then
    ok=true
    break
  fi
  sleep 2
done

if [ "$ok" != true ]; then
  warn "健康检查失败，开始回滚"
  journalctl -u agent-platform-backend.service -n 40 --no-pager >&2 || true
  journalctl -u agent-platform-runtime.service -n 40 --no-pager >&2 || true
  if [ -n "$PREVIOUS" ] && [ -d "$PREVIOUS" ]; then
    ln -sfn "$PREVIOUS" "$APP_ROOT/current"
    systemctl restart agent-platform-runtime.service || true
    systemctl restart agent-platform-backend.service || true
    die "已回滚到 $(basename "$PREVIOUS")"
  fi
  die "健康检查失败，且没有可回滚的上一个版本"
fi

# 5. 清理旧版本（保留 5 个）-------------------------------------------------
cd "$APP_ROOT/releases"
ls -1dt -- */ 2>/dev/null | tail -n +6 | while read -r old; do
  [ "$(readlink -f "$APP_ROOT/current")" = "$(readlink -f "$APP_ROOT/releases/${old%/}")" ] && continue
  rm -rf "${APP_ROOT:?}/releases/${old%/}"
  info "清理旧版本 ${old%/}"
done

log "发布成功：$VERSION"
info "前端：$WEB_ROOT"
info "后端：$BACKEND_ADDR（仅回环）"
