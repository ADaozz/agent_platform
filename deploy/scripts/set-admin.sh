#!/usr/bin/env bash
# 把平台收敛成「只有一个管理员账户」。
#
#   sudo deploy/scripts/set-admin.sh                     # 账号密码取 deploy.env 的 ADMIN_USERNAME/ADMIN_PASSWORD
#   sudo deploy/scripts/set-admin.sh --user admin --password 'your-strong-password'
#   sudo deploy/scripts/set-admin.sh --keep-others       # 只重置管理员密码，不删其它账号
#
# 做的事（一个事务内）：
#   1. 目标账号不存在就新建，存在就重置密码并置为启用；
#   2. 绑定 admin 角色（role_id=1），已有则不重复插入；
#   3. vm_host 的归属转给新管理员（避免外键挡住删除，也不丢资产数据）；
#   4. 删除其它账号及其角色、API Token、登录会话、证书申请与持有记录；
#      sys_oper_log 保留，审计轨迹不因删账号消失。
#
# 为什么重启后再启动不会长回内置账号：sqlite/data.sql 的种子改成了
# 「sys_user 为空才插入 admin/123456」，所以库里有账号时不会再种。
set -euo pipefail

HERE=$(cd "$(dirname "$0")" && pwd)
# shellcheck source=lib.sh
. "$HERE/lib.sh"

require_root
load_env

ADMIN_USERNAME=${ADMIN_USERNAME:-}
ADMIN_PASSWORD=${ADMIN_PASSWORD:-}
KEEP_OTHERS=false

usage() {
  cat <<'EOF'
用法：sudo deploy/scripts/set-admin.sh [选项]

  --user <名称>      管理员登录名（默认取 deploy.env 的 ADMIN_USERNAME）
  --password <密码>  管理员密码（默认取 deploy.env 的 ADMIN_PASSWORD）
  --keep-others      只重置该账号，不删除其它账号
  -h, --help         显示本帮助

依赖 python3-bcrypt（install-host.sh 会装）：apt-get install -y python3-bcrypt
EOF
}

while [ $# -gt 0 ]; do
  case "$1" in
    --user) ADMIN_USERNAME=${2:?--user 需要值}; shift 2 ;;
    --password) ADMIN_PASSWORD=${2:?--password 需要值}; shift 2 ;;
    --keep-others) KEEP_OTHERS=true; shift ;;
    -h | --help) usage; exit 0 ;;
    *) die "未知参数：$1（--help 看用法）" ;;
  esac
done

[ -n "$ADMIN_USERNAME" ] || die "未指定管理员登录名（--user 或 deploy.env 的 ADMIN_USERNAME）"
[ -n "$ADMIN_PASSWORD" ] || die "未指定管理员密码（--password 或 deploy.env 的 ADMIN_PASSWORD）"
case "$ADMIN_USERNAME" in
  *[[:space:]]*) die "登录名不能含空白字符" ;;
esac
if [ "${#ADMIN_PASSWORD}" -lt 8 ]; then
  die "密码至少 8 位（这是公网上的唯一管理员账号）"
fi

DB_FILE="$DATA_ROOT/data/agent-platform.db"
[ -s "$DB_FILE" ] || die "找不到数据库 $DB_FILE（先执行 install-host.sh 与 release.sh）"
require_cmd python3

# bcrypt：后端用 BCryptPasswordEncoder 校验，$2b$ 与种子的 $2a$/$2b$ 都认
if ! ADMIN_HASH=$(python3 -c 'import bcrypt' 2>/dev/null && \
  python3 -c 'import sys, bcrypt; print(bcrypt.hashpw(sys.argv[1].encode(), bcrypt.gensalt(rounds=10)).decode())' "$ADMIN_PASSWORD"); then
  die "生成 bcrypt 失败：缺少 python3-bcrypt，执行 apt-get install -y python3-bcrypt"
fi
case "$ADMIN_HASH" in
  \$2[aby]\$*) ;;
  *) die "生成的哈希格式异常：$ADMIN_HASH" ;;
esac

# SQLite 单写入者：先停后端，改完再按原状态恢复
SERVICE="agent-platform-backend.service"
WAS_RUNNING=false
if systemctl is-active --quiet "$SERVICE" 2>/dev/null; then
  WAS_RUNNING=true
  log "停止 $SERVICE（SQLite 需要独占写入）"
  systemctl stop "$SERVICE"
fi
restore_service() {
  if [ "$WAS_RUNNING" = true ]; then
    log "重启 $SERVICE"
    systemctl start "$SERVICE" || warn "$SERVICE 启动失败，检查 journalctl -u $SERVICE"
    # 不等它起来就返回，紧接着跑 healthcheck 会看到 000/502 的假失败
    wait_backend 90 && info "后端已就绪" ||
      warn "后端 90 秒内未就绪，稍后跑 deploy/scripts/healthcheck.sh 复查"
  fi
}
trap restore_service EXIT

log "写入管理员 $ADMIN_USERNAME"
python3 - "$DB_FILE" "$ADMIN_USERNAME" "$ADMIN_HASH" "$KEEP_OTHERS" <<'PY'
import sqlite3
import sys

db, user, pw_hash, keep_others = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4] == 'true'

conn = sqlite3.connect(db)
conn.execute("PRAGMA foreign_keys = ON")
try:
    conn.execute("BEGIN IMMEDIATE")

    row = conn.execute("SELECT user_id FROM sys_user WHERE user_name = ?", (user,)).fetchone()
    if row:
        uid = row[0]
        conn.execute(
            "UPDATE sys_user SET pass_word = ?, status = '0', update_time = datetime('now') "
            "WHERE user_id = ?", (pw_hash, uid))
        action = "已重置密码"
    else:
        uid = conn.execute("SELECT COALESCE(MAX(user_id), 1000) + 1 FROM sys_user").fetchone()[0]
        conn.execute(
            "INSERT INTO sys_user (user_id, user_name, pass_word, status, create_time, update_time) "
            "VALUES (?, ?, ?, '0', datetime('now'), datetime('now'))", (uid, user, pw_hash))
        action = "已新建账号"

    conn.execute("INSERT OR IGNORE INTO sys_user_role (user_id, role_id) VALUES (?, 1)", (uid,))

    # 资产归属先转移，否则 vm_host 的外键会挡住用户删除
    moved = conn.execute(
        "UPDATE vm_host SET owner_user_id = ?, update_time = datetime('now') "
        "WHERE owner_user_id IS NOT NULL AND owner_user_id <> ?", (uid, uid)).rowcount

    removed = []
    if not keep_others:
        removed = [r[0] for r in conn.execute(
            "SELECT user_name FROM sys_user WHERE user_id <> ? ORDER BY user_id", (uid,))]
        tables = ("sys_user_role", "api_token", "sys_login_session",
                  "sys_cert_apply", "sys_user_cert")
        for table in tables:
            n = conn.execute("DELETE FROM %s WHERE user_id <> ?" % table, (uid,)).rowcount
            if n:
                print("  清理 %-18s %d 行" % (table, n))
        conn.execute("DELETE FROM sys_user WHERE user_id <> ?", (uid,))

    conn.commit()

    rows = conn.execute(
        "SELECT u.user_id, u.user_name, GROUP_CONCAT(r.sys_role) "
        "FROM sys_user u LEFT JOIN sys_user_role ur ON ur.user_id = u.user_id "
        "LEFT JOIN sys_role r ON r.role_id = ur.role_id "
        "GROUP BY u.user_id, u.user_name ORDER BY u.user_id").fetchall()
finally:
    conn.close()

print("  %s：%s（user_id=%d，角色 admin）" % (user, action, uid))
if removed:
    print("  已删除账号：%s" % ", ".join(removed))
if moved:
    print("  %d 条资产归属已转给 %s" % (moved, user))
print("  当前账号：")
for user_id, name, roles in rows:
    print("    %-6d %-20s %s" % (user_id, name, roles or "(无角色)"))
if not keep_others and (len(rows) != 1 or not rows[0][2]):
    print("  警告：账号不是 1 个或缺少角色，请检查")
    sys.exit(3)
PY

info "完成。用 $ADMIN_USERNAME 登录后确认能进系统，再删掉 deploy.env 里的 ADMIN_PASSWORD 与明文凭据"
