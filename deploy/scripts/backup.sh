#!/usr/bin/env bash
# 备份：SQLite 平台库 + 证书/会话数据 + 配置密钥。
#
#   sudo deploy/scripts/backup.sh [备份目录]      # 默认 /var/backups/agent-platform
#
# 产物含 JWT/HMAC 密钥，务必按机密数据保管（异地备份前先加密）。
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"

require_root
load_env
require_cmd sqlite3 tar

DEST=${1:-/var/backups/agent-platform}
STAMP=$(date +%Y%m%d-%H%M%S)
KEEP_DAYS=${KEEP_DAYS:-14}
DB_FILE="$DATA_ROOT/data/agent-platform.db"

install -d -m 700 "$DEST"

log "备份 SQLite"
if [ -f "$DB_FILE" ]; then
  sqlite3 "$DB_FILE" 'PRAGMA wal_checkpoint(TRUNCATE);' >/dev/null
  sqlite3 "$DB_FILE" ".backup '$DEST/platform-$STAMP.sqlite'"
  chmod 600 "$DEST/platform-$STAMP.sqlite"
  info "platform-$STAMP.sqlite（$(du -h "$DEST/platform-$STAMP.sqlite" | cut -f1)）"
else
  warn "找不到 $DB_FILE，跳过数据库"
fi

log "备份数据目录（证书、会话、workspace）"
DATA_DIRS=()
for d in certs runtime; do
  [ -e "$DATA_ROOT/$d" ] && DATA_DIRS+=("$d")
done
if [ ${#DATA_DIRS[@]} -gt 0 ]; then
  tar -C "$DATA_ROOT" -czf "$DEST/data-$STAMP.tar.gz" "${DATA_DIRS[@]}"
  chmod 600 "$DEST/data-$STAMP.tar.gz"
  info "data-$STAMP.tar.gz（$(du -h "$DEST/data-$STAMP.tar.gz" | cut -f1)，含 ${DATA_DIRS[*]}）"
else
  warn "数据目录里既没有 certs 也没有 runtime，跳过"
fi

log "备份配置与密钥"
tar -C "$ETC_ROOT" -czf "$DEST/config-$STAMP.tar.gz" .
chmod 600 "$DEST/config-$STAMP.tar.gz"

log "清理 $KEEP_DAYS 天前的备份"
find "$DEST" -maxdepth 1 -type f -name '*-*.sqlite' -mtime "+$KEEP_DAYS" -delete
find "$DEST" -maxdepth 1 -type f -name '*-*.tar.gz' -mtime "+$KEEP_DAYS" -delete

log "完成"
ls -1sh "$DEST" | tail -n 8
