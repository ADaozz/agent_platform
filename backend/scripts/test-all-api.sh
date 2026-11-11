#!/usr/bin/env bash
# 测试 REST 接口，包括 AK/SK 外部业务查询鉴权
#
# 用法:
#   ./scripts/test-all-api.sh
#   BASE_URL=http://172.21.16.1:8081 API_USER=admin API_PASS=123456 ./scripts/test-all-api.sh
#   VERBOSE=1 ./scripts/test-all-api.sh          # 打印完整响应 body
#   API_TEST_FILE=docs/API-test.txt ./scripts/test-all-api.sh
#
# 依赖: curl；建议安装 jq 或 python3（解析 JSON）

set -euo pipefail

BASE_URL="${BASE_URL:-http://172.21.16.1:8081}"
API_USER="${API_USER:-admin}"
API_PASS="${API_PASS:-123456}"
NORMAL_USER="${NORMAL_USER:-user}"
NORMAL_PASS="${NORMAL_PASS:-123456}"
VERBOSE="${VERBOSE:-0}"
RUN_API_TOKEN_TESTS="${RUN_API_TOKEN_TESTS:-1}"
API_TEST_FILE="${API_TEST_FILE:-docs/API-test.txt}"
RUN_OPEN_API_TESTS="${RUN_OPEN_API_TESTS:-1}"

# 05-insert-asset-data.sql 中的测试数据
VM_HOST_ID="${VM_HOST_ID:-a1000001-0000-4000-8000-000000000001}"
VM_APP_ID="${VM_APP_ID:-b2000001-0000-4000-8000-000000000001}"

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

api_request() {
  local method="$1"
  local path="$2"
  local data="${3:-}"
  local access_key="${4:-}"
  local secret_key="${5:-}"

  local args=(
    -sS
    --noproxy '*'
    -X "$method"
    "${BASE_URL}${path}"
    -H "Content-Type: application/json"
    -H "X-Access-Key: ${access_key}"
    -H "X-Secret-Key: ${secret_key}"
    -w "\n%{http_code}"
  )
  if [[ -n "$data" ]]; then
    args+=(-d "$data")
  fi
  curl "${args[@]}"
}

load_api_test_credentials() {
  # API-test.txt 约定第一行 AK、第二行 SK；也可用环境变量覆盖。
  if [[ -n "${API_ACCESS_KEY:-}" && -n "${API_SECRET_KEY:-}" ]]; then
    return 0
  fi
  if [[ ! -f "$API_TEST_FILE" ]]; then
    info "未找到 ${API_TEST_FILE}，跳过开放接口测试"
    return 1
  fi
  mapfile -t API_TEST_CREDENTIALS < <(awk 'NF { print; if (++n == 2) exit }' "$API_TEST_FILE")
  if [[ "${#API_TEST_CREDENTIALS[@]}" -lt 2 ]]; then
    info "${API_TEST_FILE} 未包含完整 AK/SK，跳过开放接口测试"
    return 1
  fi
  API_ACCESS_KEY="${API_TEST_CREDENTIALS[0]}"
  API_SECRET_KEY="${API_TEST_CREDENTIALS[1]}"
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
section "API 开放接口：AK/SK 访问业务资源"
# ==================================================================
if [[ "$RUN_OPEN_API_TESTS" == "1" ]] && load_api_test_credentials; then
  info "GET /asset/vm （API-test.txt 中的 AK/SK）"
  assert_ok "开放接口查询虚机" \
    "$(api_request GET "/asset/vm?pageNum=1&pageSize=10" "" "$API_ACCESS_KEY" "$API_SECRET_KEY")"

  info "GET /asset/app （API-test.txt 中的 AK/SK）"
  assert_ok "开放接口查询应用" \
    "$(api_request GET "/asset/app?pageNum=1&pageSize=10" "" "$API_ACCESS_KEY" "$API_SECRET_KEY")"

  info "PUT /asset/vm （无 vm:edit 授权，预期 403）"
  assert_http "开放接口禁止修改虚机" "403" \
    "$(api_request PUT "/asset/vm" '{"hostId":"invalid","hostName":"invalid","osType":"Linux","networkZone":"idc","env":"dev"}' "$API_ACCESS_KEY" "$API_SECRET_KEY")"

  info "GET /asset/vm （错误 SK，预期 401）"
  assert_http "错误 SK 被拒绝" "401" \
    "$(api_request GET "/asset/vm?pageNum=1&pageSize=1" "" "$API_ACCESS_KEY" "${API_SECRET_KEY}invalid")"
else
  info "RUN_OPEN_API_TESTS=${RUN_OPEN_API_TESTS}，跳过开放接口测试"
fi

# ==================================================================
section "API Token：创建 AK/SK 与外部业务查询"
# ==================================================================
if [[ "$RUN_API_TOKEN_TESTS" == "1" ]]; then
  API_TOKEN_PAYLOAD='{"tokenName":"api-test","detail":"自动化测试","asset":["vm","app"]}'
  API_TOKEN_RAW=$(request POST "/api/token" "$API_TOKEN_PAYLOAD" "$ADMIN_TOKEN")
  split_response "$API_TOKEN_RAW"
  if [[ "$HTTP_CODE" == "403" ]]; then
    info "admin 未配置 api:token:add，跳过 AK/SK 测试"
  else
    assert_ok "创建 API Token" "$API_TOKEN_RAW"
    API_ACCESS_KEY=$(extract_json "$BODY" ".data.accessKey")
    API_SECRET_KEY=$(extract_json "$BODY" ".data.secretKey")
    [[ -n "$API_ACCESS_KEY" && "$API_ACCESS_KEY" != "null" ]] || fail "创建响应缺少 accessKey"
    [[ -n "$API_SECRET_KEY" && "$API_SECRET_KEY" != "null" ]] || fail "创建响应缺少 secretKey"

    info "GET /asset/vm （AK/SK）"
    assert_ok "AK/SK 查询虚机" "$(api_request GET "/asset/vm?pageNum=1&pageSize=10" "" "$API_ACCESS_KEY" "$API_SECRET_KEY")"

    info "GET /asset/app （AK/SK）"
    assert_ok "AK/SK 查询应用" "$(api_request GET "/asset/app?pageNum=1&pageSize=10" "" "$API_ACCESS_KEY" "$API_SECRET_KEY")"

    info "PUT /asset/vm （无 vm:edit 授权，预期 403）"
    assert_http "AK/SK 禁止修改虚机" "403" "$(api_request PUT "/asset/vm" '{"hostId":"invalid","hostName":"invalid","osType":"Linux","networkZone":"idc","env":"dev"}' "$API_ACCESS_KEY" "$API_SECRET_KEY")"

    info "DELETE /api/token/${API_ACCESS_KEY} （吊销）"
    assert_ok "吊销 API Token" "$(request DELETE "/api/token/${API_ACCESS_KEY}" "" "$ADMIN_TOKEN")"

    info "GET /asset/vm （吊销后预期 401）"
    assert_http "吊销后 AK/SK 失效" "401" "$(api_request GET "/asset/vm?pageNum=1&pageSize=1" "" "$API_ACCESS_KEY" "$API_SECRET_KEY")"
  fi
else
  info "RUN_API_TOKEN_TESTS=${RUN_API_TOKEN_TESTS}，跳过 AK/SK 测试"
fi

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
{"roleId":${NEW_ROLE_ID},"permissionIds":[6]}
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
section "虚机 /asset/vm"
# ==================================================================
info "GET /asset/vm （列表）"
assert_ok "虚机列表" "$(request GET "/asset/vm?pageNum=1&pageSize=10" "" "$ADMIN_TOKEN")"

info "GET /asset/vm?hostId=${VM_HOST_ID}"
assert_ok "虚机详情" "$(request GET "/asset/vm?hostId=${VM_HOST_ID}" "" "$ADMIN_TOKEN")"

info "GET /asset/vm?lifecycleStatus=running"
assert_ok "虚机按 lifecycle 筛选" "$(request GET "/asset/vm?lifecycleStatus=running" "" "$ADMIN_TOKEN")"

info "PUT /asset/vm （owner 更新 remark，再还原）"
VM_UPDATE=$(cat <<EOF
{"hostId":"${VM_HOST_ID}","hostName":"web-prod-01","osType":"CentOS","osVersion":"7.9","vmIp":"10.10.1.101","cpuCores":4,"memoryGb":8,"diskGb":100,"physicalHostIp":"192.168.1.10","networkZone":"idc","env":"prod","remark":"api-test-tmp"}
EOF
)
assert_ok "虚机更新 remark" "$(request PUT "/asset/vm" "$VM_UPDATE" "$ADMIN_TOKEN")"

VM_REVERT=$(cat <<EOF
{"hostId":"${VM_HOST_ID}","hostName":"web-prod-01","osType":"CentOS","osVersion":"7.9","vmIp":"10.10.1.101","cpuCores":4,"memoryGb":8,"diskGb":100,"physicalHostIp":"192.168.1.10","networkZone":"idc","env":"prod","remark":""}
EOF
)
assert_ok "虚机 remark 还原" "$(request PUT "/asset/vm" "$VM_REVERT" "$ADMIN_TOKEN")"

# ==================================================================
section "应用 /asset/app"
# ==================================================================
info "GET /asset/app （列表）"
assert_ok "应用列表" "$(request GET "/asset/app?pageNum=1&pageSize=10" "" "$ADMIN_TOKEN")"

info "GET /asset/app?appId=${VM_APP_ID}"
assert_ok "应用详情" "$(request GET "/asset/app?appId=${VM_APP_ID}" "" "$ADMIN_TOKEN")"

info "PUT /asset/app （owner 更新 deployPath，再还原）"
APP_UPDATE=$(cat <<EOF
{"appId":"${VM_APP_ID}","appName":"nginx-gateway","deployPath":"/opt/apps/nginx-api-test","appStatus":"running"}
EOF
)
assert_ok "应用更新 deployPath" "$(request PUT "/asset/app" "$APP_UPDATE" "$ADMIN_TOKEN")"

APP_REVERT=$(cat <<EOF
{"appId":"${VM_APP_ID}","appName":"nginx-gateway","deployPath":"/opt/apps/nginx","appStatus":"running"}
EOF
)
assert_ok "应用 deployPath 还原" "$(request PUT "/asset/app" "$APP_REVERT" "$ADMIN_TOKEN")"

# ==================================================================
section "仪表盘 /dashboard （admin）"
# ==================================================================
DASHBOARD_GETS=(
  "/dashboard/overview?scope=mine"
  "/dashboard/overview?scope=all"
  "/dashboard/summary?scope=mine"
  "/dashboard/kpi?scope=mine"
  "/dashboard/kpi?scope=all"
  "/dashboard/vm/by-lifecycle?scope=mine"
  "/dashboard/vm/by-env?scope=all"
  "/dashboard/vm/by-network-zone?scope=mine"
  "/dashboard/app/by-status?scope=mine"
  "/dashboard/trend/vm?scope=all"
  "/dashboard/rank/owner"
  "/dashboard/vm/by-physical-host"
)

for path in "${DASHBOARD_GETS[@]}"; do
  info "GET ${path}"
  assert_ok "dashboard ${path}" "$(request GET "${path}" "" "$ADMIN_TOKEN")"
done

# ==================================================================
section "定时任务 /monitor/job"
# ==================================================================
info "GET /monitor/job （列表）"
JOB_LIST_RAW=$(request GET "/monitor/job?pageNum=1&pageSize=10" "" "$ADMIN_TOKEN")
assert_ok "定时任务列表" "$JOB_LIST_RAW"
split_response "$JOB_LIST_RAW"
JOB_ID=$(extract_json "$BODY" ".data.rows[0].jobId")
[[ -n "$JOB_ID" && "$JOB_ID" != "null" ]] || fail "未找到定时任务，请确认应用已启动且 TaskRegistry 已注册任务"
ORIG_CRON=$(extract_json "$BODY" ".data.rows[0].cronExpression")
ORIG_ENABLED=$(extract_json "$BODY" ".data.rows[0].enabled")
ORIG_JOB_NAME=$(extract_json "$BODY" ".data.rows[0].jobName")
ORIG_DESC=$(extract_json "$BODY" ".data.rows[0].description")
info "测试任务 jobId=${JOB_ID} enabled=${ORIG_ENABLED} cron=${ORIG_CRON}"

info "GET /monitor/job?jobId=${JOB_ID} （详情）"
assert_ok "定时任务详情" "$(request GET "/monitor/job?jobId=${JOB_ID}" "" "$ADMIN_TOKEN")"

if [[ "$ORIG_ENABLED" == "1" ]]; then
  info "PUT /monitor/job/changeStatus （测试前先停用）"
  assert_ok "预停用定时任务" "$(request PUT "/monitor/job/changeStatus?jobId=${JOB_ID}&enabled=0" "" "$ADMIN_TOKEN")"
fi

UNCONFIGURED_CRON=""
info "PUT /monitor/job （重置为未配置 Cron 以便测试启用校验）"
JOB_RESET_DEFAULT=$(cat <<EOF
{"jobId":${JOB_ID},"jobName":"${ORIG_JOB_NAME}","cronExpression":"${UNCONFIGURED_CRON}","description":"api-test-reset","enabled":"0"}
EOF
)
assert_ok "重置定时任务为未配置 Cron" "$(request PUT "/monitor/job" "$JOB_RESET_DEFAULT" "$ADMIN_TOKEN")"

info "PUT /monitor/job/changeStatus （未配置 Cron 启用应失败）"
assert_business_error "未配置 Cron 禁止启用" \
  "$(request PUT "/monitor/job/changeStatus?jobId=${JOB_ID}&enabled=1" "" "$ADMIN_TOKEN")"

TEST_CRON="0 */30 * * * ?"
info "PUT /monitor/job （修改 Cron 为 ${TEST_CRON}）"
JOB_UPDATE=$(cat <<EOF
{"jobId":${JOB_ID},"jobName":"${ORIG_JOB_NAME}","cronExpression":"${TEST_CRON}","description":"api-test-tmp"}
EOF
)
assert_ok "修改定时任务 Cron" "$(request PUT "/monitor/job" "$JOB_UPDATE" "$ADMIN_TOKEN")"

info "PUT /monitor/job/changeStatus?enabled=1 （Switch 启用）"
assert_ok "启用定时任务" "$(request PUT "/monitor/job/changeStatus?jobId=${JOB_ID}&enabled=1" "" "$ADMIN_TOKEN")"

info "PUT /monitor/job/run （手动执行）"
assert_ok "手动执行定时任务" "$(request PUT "/monitor/job/run?jobId=${JOB_ID}" "" "$ADMIN_TOKEN")"

info "PUT /monitor/job/changeStatus?enabled=0 （Switch 停用）"
assert_ok "停用定时任务" "$(request PUT "/monitor/job/changeStatus?jobId=${JOB_ID}&enabled=0" "" "$ADMIN_TOKEN")"

info "PUT /monitor/job （还原 Cron 与描述）"
JOB_REVERT=$(cat <<EOF
{"jobId":${JOB_ID},"jobName":"${ORIG_JOB_NAME}","cronExpression":"${ORIG_CRON}","description":"${ORIG_DESC:-}","enabled":"0"}
EOF
)
assert_ok "还原定时任务配置" "$(request PUT "/monitor/job" "$JOB_REVERT" "$ADMIN_TOKEN")"

if [[ "$ORIG_ENABLED" == "1" ]]; then
  info "PUT /monitor/job/changeStatus （恢复原始启用状态）"
  assert_ok "恢复定时任务启用状态" "$(request PUT "/monitor/job/changeStatus?jobId=${JOB_ID}&enabled=1" "" "$ADMIN_TOKEN")"
fi

# ==================================================================
section "普通用户鉴权（user 角色）"
# ==================================================================
info "POST /login (${NORMAL_USER})"
USER_TOKEN=$(login_as "$NORMAL_USER" "$NORMAL_PASS") || fail "user 登录失败"
pass "user 登录成功"

info "GET /user/info （user）"
assert_ok "user 当前用户" "$(request GET "/user/info" "" "$USER_TOKEN")"

info "GET /asset/vm （user 可读）"
assert_ok "user 虚机列表" "$(request GET "/asset/vm" "" "$USER_TOKEN")"

info "GET /dashboard/overview?scope=mine （user）"
assert_ok "user dashboard mine" "$(request GET "/dashboard/overview?scope=mine" "" "$USER_TOKEN")"

info "GET /system/user （user 无权限，预期拒绝）"
assert_denied "user 访问用户管理被拒绝" "$(request GET "/system/user" "" "$USER_TOKEN")"

info "GET /dashboard/overview?scope=all （user 无 dashboard:view:all）"
assert_denied "user dashboard all 被拒绝" "$(request GET "/dashboard/overview?scope=all" "" "$USER_TOKEN")"

info "PUT /asset/vm （非 owner，预期拒绝）"
assert_denied "user 修改他人虚机被拒绝" "$(request PUT "/asset/vm" "$VM_UPDATE" "$USER_TOKEN")"

info "GET /monitor/job （user 无 monitor:job:list，预期拒绝）"
assert_denied "user 访问定时任务被拒绝" "$(request GET "/monitor/job" "" "$USER_TOKEN")"

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
