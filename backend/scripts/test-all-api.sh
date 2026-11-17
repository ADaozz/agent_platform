#!/usr/bin/env bash
# 测试当前平台仍在使用的 REST 接口
#
# 用法:
#   ./scripts/test-all-api.sh
#   BASE_URL=http://172.21.16.1:8081 API_USER=admin API_PASS=123456 ./scripts/test-all-api.sh
#   VERBOSE=1 ./scripts/test-all-api.sh          # 打印完整响应 body
#
# 依赖: curl；建议安装 jq 或 python3（解析 JSON）

set -euo pipefail

BASE_URL="${BASE_URL:-http://172.21.16.1:8081}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-123456}"
NORMAL_USER="${NORMAL_USER:-user}"
NORMAL_PASS="${NORMAL_PASS:-123456}"
VERBOSE="${VERBOSE:-0}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

PASS_COUNT=0
FAIL_COUNT=0
STEP=0

pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo -e "${GREEN}[PASS]${NC} $*"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo -e "${RED}[FAIL]${NC} $*"; exit 1; }
info() { echo -e "${YELLOW}[INFO]${NC} $*"; }
section() {
  STEP=$((STEP + 1))
  echo
  echo -e "${CYAN}========== [$STEP] $* ==========${NC}"
}

log_body() {
  if [[ "$VERBOSE" == "1" ]]; then
    echo "Body: $1"
  fi
}

# ------------------------------------------------------------------
# JSON 工具
# ------------------------------------------------------------------
extract_token() {
  local body="$1"
  if command -v jq >/dev/null 2>&1; then
    echo "$body" | jq -r '.data.token // empty'
  elif command -v python3 >/dev/null 2>&1; then
    echo "$body" | python3 -c "import sys,json; d=json.load(sys.stdin); print((d.get('data') or {}).get('token') or '')"
  else
    echo "$body" | sed -n 's/.*"token":"\([^"]*\)".*/\1/p'
  fi
}

extract_code() {
  local body="$1"
  if command -v jq >/dev/null 2>&1; then
    echo "$body" | jq -r '.code // empty'
  elif command -v python3 >/dev/null 2>&1; then
    echo "$body" | python3 -c "import sys,json; print(json.load(sys.stdin).get('code',''))"
  else
    echo "$body" | sed -n 's/.*"code":\([0-9]*\).*/\1/p'
  fi
}

extract_json() {
  local body="$1" expr="$2"
  if command -v jq >/dev/null 2>&1; then
    echo "$body" | jq -r "$expr // empty"
  elif command -v python3 >/dev/null 2>&1; then
    echo "$body" | python3 -c "
import sys, json
data = json.load(sys.stdin)
expr = '''$expr'''.strip()
# 支持 .data.rows[0].userId 等简单路径
path = expr.lstrip('.')
cur = data
for part in path.replace('[', '.').replace(']', '').split('.'):
    if not part:
        continue
    if part.isdigit():
        cur = cur[int(part)] if isinstance(cur, list) and int(part) < len(cur) else None
    else:
        cur = cur.get(part) if isinstance(cur, dict) else None
    if cur is None:
        break
print('' if cur is None else cur)
"
  else
    echo ""
  fi
}

split_response() {
  HTTP_CODE=$(echo "$1" | tail -n1)
  BODY=$(echo "$1" | sed '$d')
}

request() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local auth="${4:-}"

  local args=(
    -sS
    --noproxy '*'
    -X "$method"
    "${BASE_URL}${path}"
    -H "Content-Type: application/json"
    -w "\n%{http_code}"
  )
  if [[ -n "$auth" ]]; then
    args+=(-H "Authorization: Bearer ${auth}")
  fi
  if [[ -n "$data" ]]; then
    args+=(-d "$data")
  fi
  curl "${args[@]}"
}



login_as() {
  local user="$1" pass="$2"
  local payload
  payload=$(printf '{"userName":"%s","passWord":"%s"}' "$user" "$pass")
  split_response "$(request POST "/login" "$payload")"
  log_body "$BODY"
  if [[ "$HTTP_CODE" != "200" ]]; then
    echo -e "${RED}[FAIL]${NC} 登录 ${user} HTTP=${HTTP_CODE} | ${BODY}" >&2
    return 1
  fi
  local code token
  code=$(extract_code "$BODY")
  if [[ "$code" != "0" ]]; then
    echo -e "${RED}[FAIL]${NC} 登录 ${user} code=${code} | ${BODY}" >&2
    return 1
  fi
  token=$(extract_token "$BODY")
  if [[ -z "$token" ]]; then
    echo -e "${RED}[FAIL]${NC} 登录 ${user} 响应中无 token" >&2
    return 1
  fi
  echo "$token"
}

assert_ok() {
  local label="$1"
  split_response "$2"
  log_body "$BODY"
  echo "  HTTP ${HTTP_CODE}"
  if [[ "$HTTP_CODE" != "200" ]]; then
    fail "$label: HTTP 应为 200，实际 ${HTTP_CODE} | ${BODY}"
  fi
  local code
  code=$(extract_code "$BODY")
  if [[ "$code" != "0" ]]; then
    fail "$label: code 应为 0，实际 ${code} | ${BODY}"
  fi
  pass "$label"
}

assert_http() {
  local label="$1" expect_http="$2"
  split_response "$3"
  log_body "$BODY"
  echo "  HTTP ${HTTP_CODE}"
  if [[ "$HTTP_CODE" != "$expect_http" ]]; then
    fail "$label: HTTP 应为 ${expect_http}，实际 ${HTTP_CODE} | ${BODY}"
  fi
  pass "$label"
}

assert_denied() {
  local label="$1"
  split_response "$2"
  log_body "$BODY"
  echo "  HTTP ${HTTP_CODE}"
  local code
  code=$(extract_code "$BODY")
  if [[ "$HTTP_CODE" == "403" ]]; then
    pass "$label (HTTP 403)"
    return 0
  fi
  if [[ "$HTTP_CODE" == "200" && "$code" != "0" ]]; then
    pass "$label (code ${code})"
    return 0
  fi
  fail "$label: 预期拒绝访问，HTTP=${HTTP_CODE} code=${code} | ${BODY}"
}

assert_business_error() {
  local label="$1"
  split_response "$2"
  log_body "$BODY"
  echo "  HTTP ${HTTP_CODE}"
  if [[ "$HTTP_CODE" != "200" ]]; then
    fail "$label: HTTP 应为 200，实际 ${HTTP_CODE} | ${BODY}"
  fi
  local code
  code=$(extract_code "$BODY")
  if [[ "$code" == "0" ]]; then
    fail "$label: 预期业务失败 code!=0，实际 code=0 | ${BODY}"
  fi
  pass "$label (code ${code})"
}

# ------------------------------------------------------------------
# 开始
# ------------------------------------------------------------------
info "BASE_URL=${BASE_URL}"
info "API_USER=${API_USER}  NORMAL_USER=${NORMAL_USER}"
echo

# ==================================================================
section "认证：登录 / 未登录拦截 / 当前用户"
# ==================================================================
info "POST /login (${API_USER})"
ADMIN_TOKEN=$(login_as "$API_USER" "$API_PASS") || fail "admin 登录失败，请确认服务已启动且 BASE_URL 正确"
pass "admin 登录成功"

info "GET /user/info （无 token，预期 401）"
assert_http "未登录访问被拦截" "401" "$(request GET "/user/info")"

info "GET /user/info （admin token）"
assert_ok "admin 获取当前用户" "$(request GET "/user/info" "" "$ADMIN_TOKEN")"

# ==================================================================
section "用户管理 /system/user"
# ==================================================================
TEST_USER="apitest_$(date +%s)_${RANDOM}"

info "GET /system/user （列表）"
assert_ok "用户列表" "$(request GET "/system/user?pageNum=1&pageSize=10" "" "$ADMIN_TOKEN")"

info "GET /system/user?userId=1001 （单条）"
assert_ok "用户详情 admin" "$(request GET "/system/user?userId=1001" "" "$ADMIN_TOKEN")"

info "POST /system/user （新增 ${TEST_USER}）"
CREATE_PAYLOAD=$(cat <<EOF
{"userName":"${TEST_USER}","passWord":"123456","status":"0","roleIds":[2]}
EOF
)
assert_ok "新增用户" "$(request POST "/system/user" "$CREATE_PAYLOAD" "$ADMIN_TOKEN")"

info "GET /system/user?userName=${TEST_USER}"
LIST_RAW=$(request GET "/system/user?userName=${TEST_USER}" "" "$ADMIN_TOKEN")
assert_ok "按用户名查询" "$LIST_RAW"
split_response "$LIST_RAW"
NEW_USER_ID=$(extract_json "$BODY" ".data.rows[0].userId")
[[ -n "$NEW_USER_ID" && "$NEW_USER_ID" != "null" ]] || fail "未从列表解析到新用户 userId"
info "新用户 userId=${NEW_USER_ID}"

info "PUT /system/user （更新用户名）"
UPDATE_NAME="${TEST_USER}_upd"
UPDATE_PAYLOAD=$(cat <<EOF
{"userId":${NEW_USER_ID},"userName":"${UPDATE_NAME}","status":"0"}
EOF
)
assert_ok "更新用户" "$(request PUT "/system/user" "$UPDATE_PAYLOAD" "$ADMIN_TOKEN")"

info "PUT /system/user/authRole"
AUTH_ROLE_PAYLOAD=$(cat <<EOF
{"userId":${NEW_USER_ID},"roleIds":[2]}
EOF
)
assert_ok "分配角色" "$(request PUT "/system/user/authRole" "$AUTH_ROLE_PAYLOAD" "$ADMIN_TOKEN")"

info "GET /system/user?userId=${NEW_USER_ID}"
assert_ok "更新后用户详情" "$(request GET "/system/user?userId=${NEW_USER_ID}" "" "$ADMIN_TOKEN")"

# ==================================================================
section "角色 / 权限选项"
# ==================================================================
info "GET /system/role/options"
assert_ok "角色选项" "$(request GET "/system/role/options" "" "$ADMIN_TOKEN")"

info "GET /system/permission/options"
assert_ok "权限选项" "$(request GET "/system/permission/options" "" "$ADMIN_TOKEN")"

info "POST /system/role （新增测试角色并绑定权限）"
TEST_ROLE="apitest_role_$(date +%s)_${RANDOM}"
CREATE_ROLE_PAYLOAD=$(cat <<EOF
{"sysRole":"${TEST_ROLE}","permissionIds":[6,8]}
EOF
)
assert_ok "新增角色" "$(request POST "/system/role" "$CREATE_ROLE_PAYLOAD" "$ADMIN_TOKEN")"

info "GET /system/role?sysRole=${TEST_ROLE}"
ROLE_RAW=$(request GET "/system/role?sysRole=${TEST_ROLE}" "" "$ADMIN_TOKEN")
assert_ok "查询新增角色" "$ROLE_RAW"
split_response "$ROLE_RAW"
NEW_ROLE_ID=$(extract_json "$BODY" ".data.rows[0].roleId")
[[ -n "$NEW_ROLE_ID" && "$NEW_ROLE_ID" != "null" ]] || fail "未从列表解析到新角色 roleId"

info "PUT /system/role/authPerm （覆盖角色权限）"
ROLE_PERM_PAYLOAD=$(cat <<EOF
{"roleId":${NEW_ROLE_ID},"permissionIds":[20]}
EOF
)
assert_ok "分配角色权限" "$(request PUT "/system/role/authPerm" "$ROLE_PERM_PAYLOAD" "$ADMIN_TOKEN")"

info "PUT /system/role （更新角色标识）"
UPDATED_ROLE="${TEST_ROLE}_upd"
UPDATE_ROLE_PAYLOAD=$(cat <<EOF
{"roleId":${NEW_ROLE_ID},"sysRole":"${UPDATED_ROLE}"}
EOF
)
assert_ok "更新角色" "$(request PUT "/system/role" "$UPDATE_ROLE_PAYLOAD" "$ADMIN_TOKEN")"

info "DELETE /system/role/${NEW_ROLE_ID}"
assert_ok "删除测试角色" "$(request DELETE "/system/role/${NEW_ROLE_ID}" "" "$ADMIN_TOKEN")"

# ==================================================================
section "普通用户鉴权（user 角色）"
# ==================================================================
info "POST /login (${NORMAL_USER})"
USER_TOKEN=$(login_as "$NORMAL_USER" "$NORMAL_PASS") || fail "user 登录失败"
pass "user 登录成功"

info "GET /user/info （user）"
assert_ok "user 当前用户" "$(request GET "/user/info" "" "$USER_TOKEN")"

info "GET /system/session （user 可读）"
assert_ok "user 登录设备列表" "$(request GET "/system/session?pageNum=1&pageSize=10" "" "$USER_TOKEN")"

info "GET /system/cert/mine （user）"
assert_ok "user 我的证书" "$(request GET "/system/cert/mine" "" "$USER_TOKEN")"

info "GET /system/user （user 无权限，预期拒绝）"
assert_denied "user 访问用户管理被拒绝" "$(request GET "/system/user" "" "$USER_TOKEN")"

info "GET /system/role （user 无权限，预期拒绝）"
assert_denied "user 访问角色管理被拒绝" "$(request GET "/system/role" "" "$USER_TOKEN")"

# ==================================================================
section "清理：删除测试用户"
# ==================================================================
info "DELETE /system/user/${NEW_USER_ID}"
assert_ok "删除测试用户" "$(request DELETE "/system/user/${NEW_USER_ID}" "" "$ADMIN_TOKEN")"

# ==================================================================
echo
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}全部测试通过${NC}  PASS=${PASS_COUNT}  FAIL=${FAIL_COUNT}"
echo -e "${GREEN}========================================${NC}"
