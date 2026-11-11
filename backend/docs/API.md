# personalDemo Backend — 前端对接 API 文档

> 版本：与当前代码库同步 | 默认 Base URL：`http://<host>:8080`  
> WSL 访问 Windows 后端示例：`http://172.21.16.1:8080`（勿用 127.0.0.1）  
> 后端实现细节见 [DEVELOPMENT.md](./DEVELOPMENT.md)；解耦架构见 [DDD-DECOUPLING.md](./DDD-DECOUPLING.md)

---

## 目录

1. [通用约定](#1-通用约定)
2. [认证](#2-认证)
3. [用户管理](#3-用户管理)
4. [角色管理](#4-角色管理)
5. [权限与菜单](#5-权限与菜单)
6. [虚机管理](#6-虚机管理)
7. [应用管理](#7-应用管理)
8. [仪表盘](#8-仪表盘)
9. [API Token 与 AK/SK 鉴权](#9-api-token与aksk鉴权)
10. [定时任务](#10-定时任务)
11. [枚举与常量](#11-枚举与常量)
12. [前端集成示例](#12-前端集成示例)
13. [权限矩阵](#13-权限矩阵)
14. [客户端证书](#14-客户端证书)

---

## 1. 通用约定

### 1.1 请求头

| Header | 值 | 说明 |
|--------|-----|------|
| `Content-Type` | `application/json` | POST/PUT 必传 |
| `Authorization` | `Bearer <token>` | 除 `/login`、`/login/cert` 外必传 |

### 1.2 统一响应 `AjaxResult`

```json
{
  "code": 0,
  "msg": "成功",
  "data": { }
}
```

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | number | `0` 成功；`500` 业务/校验失败 |
| `msg` | string | 提示信息 |
| `data` | any | 业务数据；无数据时为 `null` |

### 1.3 HTTP 状态码

| HTTP | 场景 |
|------|------|
| 200 | 正常（含业务失败 `code=500`） |
| 401 | 未登录 / token 无效或过期 |
| 403 | 无接口权限（Shiro `@RequiresPermissions`） |

### 1.4 分页列表 `PageResultVO`

所有 GET 列表（传 `userId` / `hostId` / `appId` 查单条时 `total=1`）：

```json
{
  "code": 0,
  "msg": "成功",
  "data": {
    "total": 100,
    "rows": [ ]
  }
}
```

**分页参数（Query，通用）：**

| 参数 | 类型 | 默认 | 说明 |
|------|------|------|------|
| `pageNum` | int | 1 | 页码，≥1 |
| `pageSize` | int | 10 | 每页条数，最大 50 |

### 1.5 OptionVO（下拉/多选）

系统内角色、权限、owner 等统一结构：

```json
{ "id": 1, "label": "admin" }
```

- **入参**：传 `id`（如 `roleIds: [1, 2]`）
- **出参**：`roles` / `permissions` / `owner` 均为 OptionVO

### 1.6 业务错误示例

```json
{
  "code": 500,
  "msg": "资产管理错误:无权修改该虚机",
  "data": null
}
```

校验失败：

```json
{
  "code": 500,
  "msg": "用户名不能为空",
  "data": null
}
```

无权限（HTTP 403）：

```json
{
  "code": 500,
  "msg": "无权限访问",
  "data": null
}
```

---

## 2. 认证

### 2.1 登录

```
POST /login
```

**权限：** 匿名

**请求体：**

```json
{
  "userName": "admin",
  "passWord": "123456"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| userName | 是 | 最长 64 字符 |
| passWord | 是 | 最长 128 字符 |

**成功响应 `data`：**

```json
{
  "token": "eyJhbGciOiJIUzI1NiJ9...",
  "sessionId": "a1b2c3d4e5f6478990abcdef12345678",
  "user": {
    "userId": 1001,
    "username": "admin",
    "roles": [{ "id": 1, "label": "admin" }],
    "permissions": [
      { "id": 1, "label": "system:user:list" },
      { "id": 6, "label": "asset:vm:list" }
    ]
  }
}
```

> 前端应将 `token`、`sessionId` 持久化（localStorage），后续请求带 `Authorization: Bearer ${token}`。  
> JWT 内 `jti` 与 `sessionId` 相同，对应服务端 `sys_login_session`；被踢出或登出后会话失效，下次请求返回 401。  
> **单点登录：** 任意账号新登录会自动吊销其全部旧会话（`LoginSessionService.createSingleLoginSession`）。  
> 权限变更后需重新登录以刷新 `permissions`。

#### 2.1.1 客户端证书登录

证书登录经 **8443 专用 mTLS 端口**完成，不经过 443 的 `/api` 代理。详见 `docs/DEVELOPMENT.md` §17。

**浏览器流程（`redirect=1`）：**

```text
GET  https://{host}:8443/login/cert?redirect=1   → 返回自动 POST 表单
POST https://{host}:8443/login/cert?redirect=1   → 302 到 https://{host}/login#certLogin={base64 LoginVO}
```

**API 流程（无 redirect，如 curl）：**

```
POST https://{host}:8443/login/cert
```

**权限：** 匿名（Shiro `anon`）

**前置条件：**

- 浏览器已导入 **签名证** `sign.p12`（非 encrypt）
- Nginx **8443** 配置 `ssl_verify_client optional_no_ca`，并转发 `X-Client-Verify`、`X-Client-DN`、`X-Client-Cert`
- 后端只接受 `X-Client-Verify=SUCCESS`；未提交或链校验失败在 `redirect=1` 时 302 回登录页，不停留在 Nginx 400 页面
- 后端：对 `X-Client-Cert` 做 SHA-256 指纹匹配 `sys_user_cert`（`cert_type=sign`、`status=0`、未过期）

**双层校验：** Nginx 验链 + 后端指纹白名单。详见 `docs/DEVELOPMENT.md` §17.2。

**请求体：** 无

**成功响应：**

| 模式 | 响应 |
|------|------|
| `redirect=1` | HTTP 302 → `https://{host}/login#certLogin=...`（`LoginVO` 的 URL-safe Base64） |
| 无 redirect | `AjaxResult`，`data` 同账密登录（`LoginVO`） |

**失败：**

| 模式 | 响应 |
|------|------|
| `redirect=1` | HTTP 302 → `https://{host}/login?certError={message}` |
| 无 redirect | 业务异常 `code=500` |

**会话标记：** `sys_login_session.login_type = 1`（证书登录；账密为 `0`）

#### 2.1.2 mTLS 诊断（8443）

```
GET /login/cert/check
GET /login/cert/debug
```

Nginx 8443 映射：`/debug-cert`、`/cert-check` → `/login/cert/check`

**权限：** 匿名

**`/login/cert/check` 成功响应 `data`：**

| 字段 | 说明 |
|------|------|
| verify | Nginx `$ssl_client_verify`；仅 **`SUCCESS`** 可登录；`NONE`/`FAILED` 会进入后端失败重定向流程 |
| dn | 客户端证主题 DN |
| hasCert | 是否收到 `X-Client-Cert` |
| ok | 仅当 `verify=SUCCESS` 时为 `true` |

**自测期望：** `hasCert=true`, `ok=true`, **`verify=SUCCESS`**

---

### 2.2 当前用户信息

```
GET /user/info
```

**权限：** 任意登录用户（无需额外 permission）

**成功响应 `data`：** 同登录返回的 `user` 结构（`SysUserInfoVO`）。

---

### 2.3 登出

```
POST /logout
```

**权限：** 任意登录用户

**说明：** 从当前 JWT 解析 `jti=sessionId`，删除 Redis `personal-demo:session:{sessionId}`；若它仍是用户当前会话，同时删除 `personal-demo:user-active-session:{userId}`，并将 `sys_login_session.status` 更新为 `1`、写入 `revoke_time`。旧 JWT 下次请求返回 401。前端应先调用本接口，成功后再清 localStorage。

**成功响应 `data`：** `null`，`msg`: `退出成功`

---

### 2.4 登录设备管理

**Base path：** `/system/session`  
**权限前缀：** `system:session:*`

#### 2.4.1 设备列表

```
GET /system/session
```

**权限：** `system:session:list`

**Query 参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| userId | long | 仅 `system:session:manage` 可传，查指定用户 |
| userName | string | 仅 manage 可传，用户名模糊 |
| pageNum | int | 默认 1 |
| pageSize | int | 默认 10 |

无 manage 权限时，后端强制只查**当前登录用户**的设备。

**列表规则：** 查询后对 DB 中 `status=0` 的记录按 `personal-demo:session:{sessionId}` 执行 Redis `multiGet`；Key 不存在或 userId 不匹配时，本次响应按离线展示（不回写历史表）。随后按 **userId 聚合**，每个用户仅 1 行；代表会话为实时在线会话（若有）或最近一条历史；排序为 **status ASC**（在线在前）、**loginTime DESC**。

**成功响应 `data.rows[]` 字段：**

| 字段 | 说明 |
|------|------|
| sessionId | 代表会话 ID（JWT jti） |
| userId / userName | 所属用户 |
| deviceName | 由 User-Agent 解析，如 `Chrome / Windows` |
| loginIp | 登录 IP |
| loginTime | 登录时间 |
| loginType | `0` 账密 / `1` 证书 |
| status | `0` 在线 / `1` 下线 |
| current | 是否当前请求设备 |

#### 2.4.2 登录轨迹

```
GET /system/session/history?userId={userId}
```

**权限：** `system:session:list`

**说明：** 返回指定用户的**全部**历史登录记录，按 `loginTime DESC`。无 `manage` 时仅可查询当前用户。

**成功响应 `data`：** `LoginSessionVO[]`（字段同 2.4.1）

#### 2.4.3 踢出设备

```
DELETE /system/session/{sessionId}
```

**权限：** `system:session:kick`

**说明：**

- 普通用户只能踢**自己**的会话（不含本机当前会话，前端应禁用）
- 持有 `system:session:manage` 的管理员可踢任意用户会话
- 踢出后该设备 JWT 立即失效（下次请求 401）

**成功响应 `data`：** `null`，`msg`: `踢出成功`

---

## 3. 用户管理

**Base path：** `/system/user`  
**权限前缀：** `system:user:*`

### 3.1 用户列表 / 详情

```
GET /system/user
```

**权限：** `system:user:list`

**Query 参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| userId | long | 传则查单条，忽略分页 |
| userName | string | 模糊匹配 |
| status | string | `0` 正常 / `1` 停用 |
| roleId | long | 按角色筛选 |
| pageNum | int | 页码 |
| pageSize | int | 每页条数 |

**`rows[]` 元素 `SysUserVO`：**

```json
{
  "userId": 1001,
  "userName": "admin",
  "status": "0",
  "createTime": "2026-08-20 16:17:46",
  "updateTime": "2026-08-20 16:17:46",
  "lastLoginTime": null,
  "roles": [{ "id": 1, "label": "admin" }]
}
```

---

### 3.2 新增用户

```
POST /system/user
```

**权限：** `system:user:add`

**请求体：**

```json
{
  "userName": "newuser",
  "passWord": "123456",
  "status": "0",
  "roleIds": [2]
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| userName | 是 | 唯一，最长 64 |
| passWord | 是 | 6–32 位 |
| status | 否 | 默认 `0` |
| roleIds | 否 | 角色 id 列表 |

**成功：** `data` 为 `null`，`msg` 为「新增成功」。

---

### 3.3 修改用户

```
PUT /system/user
```

**权限：** `system:user:edit`

**请求体：**

```json
{
  "userId": 1002,
  "userName": "user",
  "passWord": "654321",
  "status": "0"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| userId | 是 | |
| userName | 是 | |
| passWord | 否 | 不传则不修改密码 |
| status | 否 | `0` / `1` |

**副作用（`status` 从 `0` → `1` 停用）：** 事务提交后异步级联——吊销该用户全部登录会话（Redis + DB）、API Token、客户端证书，并清理 Shiro 授权缓存。已有 JWT 立即 401；重新登录在 `AuthServiceImpl` 的 status 校验处拒绝。

---

### 3.4 分配角色（覆盖式）

```
PUT /system/user/authRole
```

**权限：** `system:user:edit`

**请求体：**

```json
{
  "userId": 1002,
  "roleIds": [2]
}
```

空数组 `[]` 表示清空该用户所有角色。

---

### 3.5 删除用户

```
DELETE /system/user/{userId}
```

**权限：** `system:user:delete`

**路径参数：** `userId` — 用户 ID

**限制：** 不能删除当前登录用户；不能删除最后一个 admin。

**副作用：** 事务提交后异步级联——吊销该用户全部登录会话、API Token、客户端证书，并清理 Shiro 授权缓存（与用户停用相同，由 `UserStatusChangedEvent(DELETED)` 触发）。

---

## 4. 角色管理

**Base path：** `/system/role`  
> 角色与权限管理仅允许具有 `admin` 角色的用户操作。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/system/role` | `system:role:list` | 分页列表/详情 |
| GET | `/system/role/options` | `system:role:list` | 下拉选项 ✅ |
| POST | `/system/role` | `system:role:add` | 新增角色，可同时绑定权限 |
| PUT | `/system/role` | `system:role:edit` | 修改角色标识 |
| PUT | `/system/role/authPerm` | `system:role:edit` | 覆盖式分配权限 |
| DELETE | `/system/role/{roleId}` | `system:role:delete` | 删除未绑定用户的角色 |

### 4.1 角色选项（常用）

```
GET /system/role/options
```

**响应 `data`：** `OptionVO[]`

```json
[
  { "id": 1, "label": "admin" },
  { "id": 2, "label": "user" }
]
```

### 4.2 分配权限（覆盖式）

```
PUT /system/role/authPerm
```

**请求体（空数组表示清空权限）：**

```json
{
  "roleId": 2,
  "permissionIds": [6, 8]
}
```

> **授权入口统一走权限树**：`permissionIds` 请通过 [5.2 菜单权限树](#52-菜单权限树) 取回并勾选后提交，树的权限叶子 `id` 就是这里的 `permissionId`。新增角色走 `POST /system/role`（同样带 `permissionIds`），编辑角色走本接口，二者共用同一棵树，无需再拉扁平权限列表。
>
> `admin` 角色由后端强制授予全部权限，提交任何 `permissionIds` 都会被覆盖为全量，前端应把该角色的勾选框置灰。

**list 基础权限（自动补全）：**

非 admin 角色在 `POST /system/role`、`PUT /system/role/authPerm` 保存时，若 `permissionIds` 中含某模块的 `add` / `edit` / `delete`，后端会自动追加同前缀的 `list` 再入库。例如只提交 `[3]`（`system:user:edit`），实际绑定为 `[1, 3]`（list + edit）。

| 场景 | 说明 |
|------|------|
| 只勾 edit 保存 | 后端补 list；用户可见菜单、可调列表、仅显示编辑按钮 |
| 只勾 list | 只读进入模块，无 add/edit/delete 按钮 |
| 取消 list（前端） | 同菜单下 add/edit/delete 联动取消后再提交 |

前端授权弹窗已做相同联动；最终以**后端写入结果**为准，重新打开编辑应能看到补全后的 list。

### 4.3 角色列表里的已绑定权限

`GET /system/role` 返回的 `SysRoleVO.permissions` 为 `OptionVO[]`，其中：

| 字段 | 说明 |
|------|------|
| `id` | `permissionId` |
| `label` | **权限中文名**（`sys_permission.perm_name`），未维护中文名时回退为权限标识 |

```json
{
  "roleId": 2,
  "sysRole": "user",
  "permissions": [
    { "id": 6, "label": "虚拟机查询" },
    { "id": 8, "label": "应用查询" }
  ]
}
```

> 注意：`label` 以前是 `system:user:list` 这样的权限标识，现在是中文名，用于列表直接展示。若需要权限标识请从权限树的 `permission` 字段取。

---

## 5. 权限与菜单

**Base path：** `/system/permission`、`/system/menu`
> 均仅允许具有 `admin` 角色的用户调用。

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/system/permission` | `system:role:list` | 分页列表/详情，仅管理员 |
| GET | `/system/permission/options` | `system:role:list` | 全部权限选项 ✅ |
| GET | `/system/menu/permTree` | `system:role:list` | 菜单+权限树，按角色回显勾选 ✅ |

### 5.1 权限选项

```
GET /system/permission/options
```

**响应 `data`：** `OptionVO[]`

```json
[
  { "id": 1, "label": "system:user:list" },
  { "id": 6, "label": "asset:vm:list" }
]
```

### 5.2 菜单权限树

权限按归属菜单分组后返回两级树，用于角色授权弹窗直接渲染。菜单来自 `sys_menu`，权限通过 `sys_permission.menu_id` 挂到菜单下。

```
GET /system/menu/permTree?roleId=2
```

**请求参数：**

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `roleId` | Long | 否 | 传则按该角色回显 `checked`；不传则所有权限节点 `checked` 均为 `false`，用于「新增角色」场景 |

> `roleId` 指向 `admin` 角色时所有权限恒为 `checked: true`——后端授权时对 admin 强制全量授权，前端可据此把复选框置灰。

**响应 `data`：** `PermTreeNodeVO[]`

| 字段 | 类型 | 出现节点 | 说明 |
|------|------|----------|------|
| `id` | Long | 全部 | 菜单节点为 `menuId`，权限节点为 `permissionId`。**授权提交用的就是权限节点的这个值** |
| `nodeKey` | String | 全部 | `"M-1"` / `"P-17"`。`menuId` 与 `permissionId` 各自从 1 开始会撞号，树组件的 `node-key` 请用它，不要用 `id` |
| `name` | String | 全部 | 菜单名或权限中文名（权限未维护中文名时回退为权限标识） |
| `type` | String | 全部 | `MENU` 或 `PERMISSION` |
| `permission` | String | 仅 PERMISSION | 权限标识，例如 `system:user:list` |
| `checked` | Boolean | 仅 PERMISSION | 该角色是否已勾选 |
| `children` | Array | 仅 MENU | 子节点，菜单下无权限时为 `[]` |

> 注意：菜单节点**不会**出现 `permission`、`checked` 两个键，权限节点**不会**出现 `children` 键（后端 `@JsonInclude(NON_NULL)` 直接省略）。写 TS 类型时这几个字段要声明为可选，不要按「恒存在」处理。
>
> 若存在未挂到任何菜单的权限，会统一归入 `id: 0`、`name: "未分类"` 的兜底菜单节点，不会丢失。

**响应示例**（`roleId=2`，即 user 角色，仅勾中 `asset:vm:list`、`asset:app:list`）：

```json
{
  "code": 200,
  "msg": "成功",
  "data": [
    {
      "id": 1,
      "nodeKey": "M-1",
      "name": "仪表盘",
      "type": "MENU",
      "children": [
        { "id": 9, "nodeKey": "P-9", "name": "全局数据查看", "type": "PERMISSION", "permission": "dashboard:view:all", "checked": false }
      ]
    },
    {
      "id": 2,
      "nodeKey": "M-2",
      "name": "虚拟机",
      "type": "MENU",
      "children": [
        { "id": 6, "nodeKey": "P-6", "name": "虚拟机查询", "type": "PERMISSION", "permission": "asset:vm:list", "checked": true },
        { "id": 7, "nodeKey": "P-7", "name": "虚拟机删除", "type": "PERMISSION", "permission": "asset:vm:delete", "checked": false }
      ]
    },
    {
      "id": 3,
      "nodeKey": "M-3",
      "name": "应用服务",
      "type": "MENU",
      "children": [
        { "id": 8, "nodeKey": "P-8", "name": "应用查询", "type": "PERMISSION", "permission": "asset:app:list", "checked": true }
      ]
    },
    {
      "id": 4,
      "nodeKey": "M-4",
      "name": "用户管理",
      "type": "MENU",
      "children": [
        { "id": 1, "nodeKey": "P-1", "name": "用户查询", "type": "PERMISSION", "permission": "system:user:list", "checked": false },
        { "id": 2, "nodeKey": "P-2", "name": "用户新增", "type": "PERMISSION", "permission": "system:user:add", "checked": false },
        { "id": 3, "nodeKey": "P-3", "name": "用户编辑", "type": "PERMISSION", "permission": "system:user:edit", "checked": false },
        { "id": 4, "nodeKey": "P-4", "name": "用户删除", "type": "PERMISSION", "permission": "system:user:delete", "checked": false }
      ]
    },
    {
      "id": 5,
      "nodeKey": "M-5",
      "name": "角色管理",
      "type": "MENU",
      "children": [
        { "id": 5, "nodeKey": "P-5", "name": "角色查询", "type": "PERMISSION", "permission": "system:role:list", "checked": false },
        { "id": 14, "nodeKey": "P-14", "name": "角色新增", "type": "PERMISSION", "permission": "system:role:add", "checked": false },
        { "id": 15, "nodeKey": "P-15", "name": "角色编辑", "type": "PERMISSION", "permission": "system:role:edit", "checked": false },
        { "id": 16, "nodeKey": "P-16", "name": "角色删除", "type": "PERMISSION", "permission": "system:role:delete", "checked": false }
      ]
    },
    {
      "id": 6,
      "nodeKey": "M-6",
      "name": "定时任务",
      "type": "MENU",
      "children": [
        { "id": 17, "nodeKey": "P-17", "name": "任务查询", "type": "PERMISSION", "permission": "monitor:job:list", "checked": false },
        { "id": 18, "nodeKey": "P-18", "name": "任务编辑", "type": "PERMISSION", "permission": "monitor:job:edit", "checked": false }
      ]
    },
    {
      "id": 7,
      "nodeKey": "M-7",
      "name": "API 开放接口",
      "type": "MENU",
      "children": [
        { "id": 10, "nodeKey": "P-10", "name": "令牌查询", "type": "PERMISSION", "permission": "api:token:list", "checked": false },
        { "id": 11, "nodeKey": "P-11", "name": "令牌新增", "type": "PERMISSION", "permission": "api:token:add", "checked": false },
        { "id": 12, "nodeKey": "P-12", "name": "令牌详情", "type": "PERMISSION", "permission": "api:token:get", "checked": false },
        { "id": 13, "nodeKey": "P-13", "name": "令牌吊销", "type": "PERMISSION", "permission": "api:token:delete", "checked": false }
      ]
    },
    {
      "id": 8,
      "nodeKey": "M-8",
      "name": "登录设备管理",
      "type": "MENU",
      "children": [
        { "id": 20, "nodeKey": "P-20", "name": "设备查询", "type": "PERMISSION", "permission": "system:session:list", "checked": false },
        { "id": 21, "nodeKey": "P-21", "name": "踢出设备", "type": "PERMISSION", "permission": "system:session:kick", "checked": false },
        { "id": 22, "nodeKey": "P-22", "name": "设备管理", "type": "PERMISSION", "permission": "system:session:manage", "checked": false }
      ]
    }
  ]
}
```

**错误响应：**

| 场景 | 响应 `msg` |
|------|-----------|
| 调用者不是 admin 角色 | `系统管理错误:仅管理员可以操作角色和权限` |
| `roleId` 对应角色不存在 | `系统管理错误:角色不存在` |

均为 `code: 500` 的业务错误，格式见 [1.6](#16-业务错误示例)。

前端对接写法见 [12.6 角色授权树](#126-角色授权树)。

---

## 6. 虚机管理

**Base path：** `/asset/vm`

### 6.1 虚机列表 / 详情

```
GET /asset/vm
```

**权限：** 登录即可（全员可见全部虚机）

**Query 参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| hostId | string | UUID，传则查单条 |
| hostName | string | 模糊 |
| vmIp | string | 模糊 |
| lifecycleStatus | string | 见 [生命周期枚举](#111-虚机生命周期) |
| ownerUserId | long | 按 owner 筛选 |
| networkZone | string | `idc` / `cfdc` |
| env | string | `prod` / `dev` / `test` |
| pageNum / pageSize | int | 分页 |

**`rows[]` 元素 `VmHostVO`：**

```json
{
  "hostId": "a1000001-0000-4000-8000-000000000001",
  "hostName": "web-prod-01",
  "osType": "CentOS",
  "osVersion": "7.9",
  "vmIp": "10.10.1.101",
  "cpuCores": 4,
  "memoryGb": 8,
  "diskGb": 100,
  "physicalHostIp": "192.168.1.10",
  "lifecycleStatus": "running",
  "owner": { "id": 1001, "label": "admin" },
  "networkZone": "idc",
  "env": "prod",
  "remark": null,
  "createTime": "2026-08-21 15:59:24",
  "updateTime": "2026-08-21 15:59:24"
}
```

---

### 6.2 修改虚机

```
PUT /asset/vm
```

**权限：** 登录 + **当前用户必须是该虚机 `owner`**（与 `system:permission` 无关）

**不提供** 新增、删除接口。

**请求体：**

```json
{
  "hostId": "a1000001-0000-4000-8000-000000000001",
  "hostName": "web-prod-01",
  "osType": "CentOS",
  "osVersion": "7.9",
  "vmIp": "10.10.1.101",
  "cpuCores": 4,
  "memoryGb": 8,
  "diskGb": 100,
  "physicalHostIp": "192.168.1.10",
  "lifecycleStatus": "stopped",
  "networkZone": "idc",
  "env": "prod",
  "remark": "备注"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| hostId | 是 | UUID |
| hostName | 是 | |
| osType | 是 | |
| networkZone | 是 | `idc` / `cfdc` |
| env | 是 | `prod` / `dev` / `test` |
| lifecycleStatus | 否 | 不传则保持；传则只能 **推进一步**，见生命周期 |

**生命周期流转：** `creating → running → stopped → pending_delete → destroyed`（不可跳步、不可回退）

**副作用：** 修改 `vmIp` 时，会自动同步该虚机下所有应用的 `vmIp`。

**常见错误：**

| msg | 原因 |
|-----|------|
| 无权修改该虚机 | 非 owner |
| 虚机已销毁，不可修改 | lifecycle 为 destroyed |
| creating -> stopped | 非法跳步 |

---

## 7. 应用管理

**Base path：** `/asset/app`

### 7.1 应用列表 / 详情

```
GET /asset/app
```

**权限：** 登录即可

**Query 参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| appId | string | UUID，传则查单条 |
| appName | string | 模糊 |
| hostId | string | 所属虚机 |
| vmIp | string | 模糊 |
| appStatus | string | `running` / `stopped` |
| pageNum / pageSize | int | 分页 |

**`rows[]` 元素 `VmAppVO`：**

```json
{
  "appId": "b2000001-0000-4000-8000-000000000001",
  "appName": "nginx-gateway",
  "hostId": "a1000001-0000-4000-8000-000000000001",
  "vmIp": "10.10.1.101",
  "deployPath": "/opt/apps/nginx",
  "appStatus": "running",
  "createTime": "2026-08-21 15:59:24",
  "updateTime": "2026-08-21 15:59:24"
}
```

---

### 7.2 修改应用

```
PUT /asset/app
```

**权限：** 登录 + **必须是关联虚机的 owner**

**请求体：**

```json
{
  "appId": "b2000001-0000-4000-8000-000000000001",
  "appName": "nginx-gateway",
  "deployPath": "/opt/apps/nginx",
  "appStatus": "running"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| appId | 是 | |
| appName | 是 | |
| deployPath | 是 | |
| appStatus | 是 | `running` / `stopped` |

---

## 8. 仪表盘

**Base path：** `/dashboard`  
**权限：** 登录即可；`scope=all` 额外需要 `dashboard:view:all`

### 8.1 scope 参数

| 值 | 说明 |
|----|------|
| `mine`（默认） | 仅统计 `owner_user_id = 当前用户` 的虚机；应用通过 JOIN 虚机过滤 |
| `all` | 全平台统计；需 `dashboard:view:all` |

### 8.2 接口列表

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/dashboard/overview` | 首屏聚合（推荐） |
| GET | `/dashboard/summary` | 同 overview |
| GET | `/dashboard/kpi` | 仅 KPI 卡片 |
| GET | `/dashboard/vm/by-lifecycle` | 虚机生命周期饼图 |
| GET | `/dashboard/vm/by-env` | 虚机环境饼图 |
| GET | `/dashboard/vm/by-network-zone` | 虚机网段饼图 |
| GET | `/dashboard/app/by-status` | 应用状态饼图 |
| GET | `/dashboard/trend/vm` | 虚机按月新增趋势 |
| GET | `/dashboard/rank/owner` | owner 排行 Top10（仅 all） |
| GET | `/dashboard/vm/by-physical-host` | 宿主机分布 Top10（仅 all） |

**Query：** `scope=mine|all`（除 rank/physical-host 仅 all 有效外，均可传 scope）

### 8.3 响应结构（overview）

```json
{
  "code": 0,
  "msg": "成功",
  "data": {
    "kpi": {
      "scope": "mine",
      "vmHostCount": 3,
      "vmHostRunningCount": 2,
      "vmAppCount": 2,
      "cpuCoresTotal": 14,
      "memoryGbTotal": 28,
      "userCount": null
    },
    "vmByLifecycle": {
      "data": [
        { "name": "running", "value": 2 },
        { "name": "stopped", "value": 1 }
      ]
    },
    "vmByEnv": {
      "data": [
        { "name": "prod", "value": 1 },
        { "name": "dev", "value": 1 }
      ]
    },
    "vmByNetworkZone": {
      "data": [
        { "name": "idc", "value": 2 },
        { "name": "cfdc", "value": 1 }
      ]
    },
    "appByStatus": {
      "data": [{ "name": "running", "value": 2 }]
    },
    "vmCreateTrend": {
      "categories": ["2026-08"],
      "series": [
        { "name": "新增虚机", "data": [3] }
      ]
    },
    "ownerRank": null,
    "physicalHostDistribution": null
  }
}
```

> `scope=mine` 时 `ownerRank`、`physicalHostDistribution` 为 `null`。  
> `scope=all` 时 `kpi.userCount` 有值；上述两图表有数据。

### 8.4 ECharts 对接

**饼图 / 环形图：**

```javascript
const pie = res.data.vmByLifecycle;
option = {
  series: [{
    type: 'pie',
    radius: '60%',
    data: pie.data   // [{ name, value }, ...]
  }]
};
```

**折线图 / 柱状图：**

```javascript
const trend = res.data.vmCreateTrend;
option = {
  xAxis: { type: 'category', data: trend.categories },
  yAxis: { type: 'value' },
  series: trend.series.map(s => ({ ...s, type: 'line' }))
};
```

**KPI 卡片：** 直接绑定 `res.data.kpi` 各数字字段。

### 8.5 图表 VO 字段说明

**PieChartVO**

| 字段 | 说明 |
|------|------|
| data | `{ name: string, value: number }[]` → ECharts `series.data` |

**CategoryChartVO**

| 字段 | 说明 |
|------|------|
| categories | string[] → ECharts `xAxis.data` |
| series | `{ name: string, data: number[] }[]` → ECharts `series`（前端补 `type`） |

**DashboardKpiVO**

| 字段 | 说明 |
|------|------|
| scope | `mine` / `all` |
| vmHostCount | 虚机总数 |
| vmHostRunningCount | running 虚机数 |
| vmAppCount | 应用总数 |
| cpuCoresTotal | CPU 核数合计 |
| memoryGbTotal | 内存 GB 合计 |
| userCount | 用户数（仅 all） |

---

## 9. API Token 与 AK/SK 鉴权

API Token 管理接口使用登录 JWT；创建成功后返回一对给外部系统使用的
`accessKey`（AK）和 `secretKey`（SK）。SK 只在创建响应中返回，列表接口不会返回
SK。

| 方法 | 路径 | 权限 |
|------|------|------|
| GET | `/api/token` | `api:token:list` |
| POST | `/api/token` | `api:token:add` |
| GET | `/api/token/user/{userId}` | `api:token:get` |
| GET | `/api/token/grantOptions` | `api:token:add` |
| DELETE | `/api/token/{accessKey}` | `api:token:delete` |
| GET | `/api/open/doc` | `api:token:list` |

### 9.1 创建 Token

```http
POST /api/token
Authorization: Bearer <登录 JWT>
Content-Type: application/json
```

请求体：

```json
{
  "tokenName": "Jenkins CI/CD",
  "detail": "部署流水线读取资产信息",
  "asset": ["vm", "app"]
}
```

`asset` 必填，格式为 `{resource}:{action}`；兼容旧值 `vm`、`app`（等同 `vm:list`、`app:list`）：

| 值 | 说明 | 对应开放接口 |
|----|------|--------------|
| `vm:list` / `vm` | 虚拟机查询 | `GET /asset/vm` |
| `vm:edit` | 虚拟机修改 | `PUT /asset/vm`（仅 owner） |
| `app:list` / `app` | 应用查询 | `GET /asset/app` |
| `app:edit` | 应用修改 | `PUT /asset/app`（仅虚机 owner） |

> `vm:add` / `vm:delete` / `app:add` / `app:delete` 可在创建 Token 时勾选，但后端尚未提供对应 POST/DELETE 开放接口。

创建 Token 时可勾选的全部能力：

```
GET /api/token/grantOptions
```

**权限：** `api:token:add`  
**响应 `data`：** 分组列表 `[{ key, name, options: [{ value, label }] }]`

创建成功响应：

```json
{
  "code": 0,
  "msg": "新增成功",
  "data": {
    "accessKey": "ak-...",
    "secretKey": "eyJhbGciOiJIUzI1NiJ9...",
    "tokenName": "Jenkins CI/CD",
    "asset": ["vm", "app"],
    "status": "0",
    "expireTime": "2026-08-31 12:00:00"
  }
}
```

同一用户最多创建 3 个有效 Token。吊销后 `status=1`，已吊销 Token 立即失效。

### 9.2 外部系统使用 AK/SK

外部系统请求业务接口时携带：

```http
X-Access-Key: ak-...
X-Secret-Key: eyJhbGciOiJIUzI1NiJ9...
```

当前 AK/SK 可访问的开放接口（须 Token `asset` 含对应 grant）：

| 方法 | 路径 | 所需 grant |
|------|------|------------|
| GET | `/asset/vm` | `vm:list` 或 `vm` |
| PUT | `/asset/vm` | `vm:edit` |
| GET | `/asset/app` | `app:list` 或 `app` |
| PUT | `/asset/app` | `app:edit` |

查询示例：

```bash
curl --noproxy '*' \
  -H "X-Access-Key: ak-..." \
  -H "X-Secret-Key: eyJhbGciOiJIUzI1NiJ9..." \
  "http://<host>:8080/asset/vm?pageNum=1&pageSize=10"
```

服务端依次校验：

1. SK 的 JWT 签名、类型和有效期；
2. 请求头 AK 与 SK 中的 AK 是否一致；
3. AK 对应的数据库记录、用户 ID、状态和过期时间；
4. Token 的 `asset` 是否包含当前路径与方法所需的 grant（如 `vm:list`）；
5. PUT 时 Service 层校验 `ownerUserId = Token 所属用户`。

没有对应 grant 的 Token 访问业务接口返回 HTTP 403。Token 管理接口与 `/api/open/doc` 仍须登录 JWT。

### 9.3 开放接口动态文档

前端「API 开放接口 → 接口文档」Tab 的数据源。

```
GET /api/open/doc
```

**权限：** `api:token:list`

**说明：** 返回当前登录用户 Shiro 权限范围内可调用的开放接口元数据（参数说明、请求/响应示例、所需 grant）。未实现或未授权的接口不会出现在列表中。

**成功响应 `data` 结构：**

```json
{
  "baseUrl": "/api",
  "auth": {
    "type": "AK_SK",
    "headers": [
      { "name": "X-Access-Key", "required": true },
      { "name": "X-Secret-Key", "required": true }
    ],
    "note": "外部系统调用须携带 AK/SK；平台内调试可选用登录 JWT 或 AK/SK"
  },
  "operations": [
    {
      "id": "vm-list",
      "groupKey": "vm",
      "groupName": "虚拟机",
      "grant": "vm:list",
      "requiredPermission": "asset:vm:list",
      "method": "GET",
      "path": "/asset/vm",
      "summary": "查询虚机列表",
      "description": "...",
      "queryParams": [],
      "bodyParams": [],
      "requestBodyExample": null,
      "responseExample": { "code": 0, "msg": "成功", "data": {} },
      "allowed": true
    }
  ]
}
```

**前端能力：** 根据 `operations` 渲染文档，并生成 Python3 / Java / curl / C 调用示例；支持 JWT 或 AK/SK 在线调试。

---

## 10. 定时任务

**Base path：** `/monitor/job`

任务由后端代码扫描 `@TaskInfo` 注解自动注册，**不提供新增/删除接口**。

### 10.1 接口一览

| 方法 | 路径 | 权限 | 说明 |
|------|------|------|------|
| GET | `/monitor/job` | `monitor:job:list` | 分页列表；传 `jobId` 查单条 |
| PUT | `/monitor/job` | `monitor:job:edit` | 修改名称、Cron、描述、启用状态 |
| PUT | `/monitor/job/changeStatus?jobId=&enabled=` | `monitor:job:edit` | 快捷启用/停用 |
| PUT | `/monitor/job/run?jobId=` | `monitor:job:edit` | 手动执行（须已启用） |

### 10.2 列表 / 详情

**GET** `/monitor/job?jobName=&enabled=&pageNum=1&pageSize=10`

**GET** `/monitor/job?jobId=1234567890`（单条）

**响应 data：**

```json
{
  "total": 2,
  "rows": [
    {
      "jobId": 1234567890,
      "jobName": "系统汇报",
      "beanName": "sysReportTask",
      "jobGroup": "DEFAULT",
      "cronExpression": "0 */5 * * * ?",
      "description": "汇报系统状况",
      "status": "2",
      "enabled": "1",
      "createTime": "2026-08-25 10:00:00",
      "updateTime": "2026-08-25 12:00:00"
    }
  ]
}
```

**列表字段展示约定：**

| 字段 | 前端组件 | 说明 |
|------|----------|------|
| `enabled` | **Switch 开关** | 见 [10.4 启用 / 停用](#104-启用--停用) |
| `status` | **彩色状态光点** | 见 [10.6 执行状态光点](#106-执行状态光点) |

### 10.3 修改任务

**PUT** `/monitor/job`

```json
{
  "jobId": 1234567890,
  "jobName": "系统汇报",
  "cronExpression": "0 */5 * * * ?",
  "description": "每5分钟汇报一次",
  "enabled": "1"
}
```

- `beanName` 不可改，由代码扫描决定
- **未配置**的 Cron 为空字符串 `""`（扫描注册的新任务默认如此）；**启用前**须填写合法表达式
- `0 0 0 * * ?` 表示每天 0 点，是**合法** Cron，可按需启用

### 10.4 启用 / 停用

**接口：** `PUT /monitor/job/changeStatus?jobId=1234567890&enabled=1`

| 参数 | 值 | 含义 |
|------|-----|------|
| `enabled` | `0` | 停用 |
| `enabled` | `1` | 启用 |

**前端必须使用 Switch 开关（switch button），不要用普通按钮或下拉框。**

| 约定 | 说明 |
|------|------|
| 组件 | `el-switch` / Ant Design `Switch` 等开关组件 |
| 绑定 | 开 = `enabled === '1'`，关 = `enabled === '0'` |
| 交互 | 切换时调用 `PUT /monitor/job/changeStatus`；**不要**在列表 Switch 上走 `PUT /monitor/job` 整表更新 |
| 权限 | 无 `monitor:job:edit` 时 Switch 设为 `disabled` |
| 失败回滚 | 接口失败（如 Cron 未配置）时 Switch **回弹**到切换前状态，并提示后端 `msg` |
| 文案 | 开：启用；关：停用（可选在 Switch 旁显示文字） |

**Switch 切换示例：**

```javascript
async function onEnabledChange(row, nextEnabled) {
  const prev = row.enabled;
  row.enabled = nextEnabled; // 乐观更新（可选）
  try {
    await request.put('/monitor/job/changeStatus', null, {
      params: { jobId: row.jobId, enabled: nextEnabled },
    });
  } catch (e) {
    row.enabled = prev; // 失败回滚
  }
}
```

### 10.5 手动执行

**PUT** `/monitor/job/run?jobId=1234567890`

任务须 `enabled=1`，执行结果写入 `sys_job_log`。

### 10.6 执行状态光点

字段 `status` 表示**最近一次执行状态**（`0` 未执行 / `1` 正在执行 / `2` 执行成功 / `3` 执行失败）。列表与详情中须用**不同颜色的圆点（光点）**展示，建议搭配简短文字。

| `status` | 含义 | 光点颜色 | 推荐色值 | 动效 |
|----------|------|----------|----------|------|
| `0` | 未执行 | 灰色 | `#909399` | 无 |
| `1` | 正在执行 | 蓝色 | `#409EFF` | 可选呼吸/脉冲动画 |
| `2` | 执行成功 | 绿色 | `#67C23A` | 无 |
| `3` | 执行失败 | 红色 | `#F56C6C` | 无 |

**展示格式：** `[光点] 文案`，例如 `🟢 执行成功`（实际用 CSS 圆点，勿用 emoji 替代光点组件）。

**光点样式参考：**

```css
.job-status-dot {
  display: inline-block;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  margin-right: 6px;
  vertical-align: middle;
}
.job-status-dot--idle    { background: #909399; }
.job-status-dot--running { background: #409EFF; animation: pulse 1.2s infinite; }
.job-status-dot--success { background: #67C23A; }
.job-status-dot--failure { background: #F56C6C; }
```

**Vue 示例：**

```vue
<span class="job-status">
  <i :class="['job-status-dot', dotClass(row.status)]" />
  {{ statusLabel(row.status) }}
</span>
```

```javascript
const STATUS_MAP = {
  '0': { class: 'job-status-dot--idle',    label: '未执行' },
  '1': { class: 'job-status-dot--running', label: '正在执行' },
  '2': { class: 'job-status-dot--success', label: '执行成功' },
  '3': { class: 'job-status-dot--failure', label: '执行失败' },
};
```

> `enabled`（启用/停用）与 `status`（执行状态）含义不同：前者用 Switch 控制是否参与调度；后者只读展示，用彩色光点区分。

---

## 11. 枚举与常量

### 11.1 虚机生命周期 `lifecycleStatus`

```
creating → running → stopped → pending_delete → destroyed
```

只能按箭头 **推进一步**，不可跳步、不可回退。

### 11.2 应用状态 `appStatus`

| 值 | 说明 |
|----|------|
| running | 运行中 |
| stopped | 已停止 |

### 11.3 网段 `networkZone`

| 值 | 说明 |
|----|------|
| idc | IDC 机房 |
| cfdc | CFDC |

### 11.4 环境 `env`

| 值 | 说明 |
|----|------|
| prod | 生产 |
| dev | 开发 |
| test | 测试 |

### 11.5 用户状态 `status`

| 值 | 说明 |
|----|------|
| 0 | 正常 |
| 1 | 停用 |

### 11.6 仪表盘 scope

| 值 | 说明 |
|----|------|
| mine | 我的资源（owner 过滤） |
| all | 全局（需 `dashboard:view:all`） |

### 11.7 定时任务 `enabled`（启用状态）

| 值 | 说明 | 前端 |
|----|------|------|
| 0 | 停用（新建默认，不参与调度） | Switch **关** |
| 1 | 启用（按 Cron 调度，可手动 run） | Switch **开** |

### 11.8 定时任务 `status`（最近执行状态）

| 值 | 说明 | 光点颜色 |
|----|------|----------|
| 0 | 未执行 | 灰 `#909399` |
| 1 | 正在执行 | 蓝 `#409EFF`（可脉冲） |
| 2 | 执行成功 | 绿 `#67C23A` |
| 3 | 执行失败 | 红 `#F56C6C` |

### 11.9 定时任务日志 `sys_job_log.status`

| 值 | 说明 |
|----|------|
| 0 | 成功 |
| 1 | 失败 |

---

## 12. 前端集成示例

### 12.1 Axios 封装

```javascript
import axios from 'axios';

const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || 'http://172.21.16.1:8080',
  timeout: 30000,
});

request.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

request.interceptors.response.use(
  (res) => {
    const { code, msg, data } = res.data;
    if (code === 0) return data;
    return Promise.reject(new Error(msg || '请求失败'));
  },
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      // router.push('/login')
    }
    if (err.response?.status === 403) {
      // 无权限提示
    }
    return Promise.reject(err);
  }
);

export default request;
```

### 12.2 登录

```javascript
export function login(userName, passWord) {
  return request.post('/login', { userName, passWord });
}

// 使用
const data = await login('admin', '123456');
localStorage.setItem('token', data.token);
```

### 12.3 权限按钮与菜单控制

```javascript
function hasPerm(permissions, perm) {
  return permissions.some(p => p.label === perm);
}

// 来自 login 或 /user/info 的 user.permissions
hasPerm(user.permissions, 'system:user:add'); // 控制「新增用户」按钮
```

**菜单 / 路由入口：** 系统管理类页面（用户、角色、定时任务、API Token、登录设备）需对应模块的 `*:list` 才显示菜单并通过路由守卫。虚机、应用、仪表盘无此限制或另有规则（如 `dashboard:view:all` 控制全局数据）。

**角色授权联动（前端 `RoleListView`）：**

| 操作 | 行为 |
|------|------|
| 勾选 add / edit / delete | 同菜单分组自动勾选 list |
| 取消 list | 同分组 add / edit / delete 一并取消 |
| 保存 | 后端再次补全 list（见 [4.2](#42-分配权限覆盖式)） |

### 12.4 分页列表

```javascript
export function listUsers(params) {
  return request.get('/system/user', { params });
}

// { pageNum: 1, pageSize: 10, userName: 'admin' }
// 返回 { total, rows }
```

### 12.5 仪表盘首屏

```javascript
export function getDashboardOverview(scope = 'mine') {
  return request.get('/dashboard/overview', { params: { scope } });
}
```

### 12.6 角色授权树

角色的权限分配统一从这棵树进出：读用 `GET /system/menu/permTree`，写复用 `POST /system/role`（新增）和 `PUT /system/role/authPerm`（编辑）。树里权限节点的 `id` 就是 `permissionId`，与 `permissionIds` 是同一套 ID，勾选结果可直接提交，无需任何映射转换。

接口只对 `admin` 角色开放（后端 `assertAdmin`），前端可用登录返回的 `user.roles` 判断后再决定是否渲染授权 UI：

```javascript
const isAdmin = (user.roles ?? []).some((r) => r.label === 'admin');
```

```javascript
// 打开授权弹窗：新增角色不传 roleId，编辑角色传 roleId 回显勾选
export function getPermTree(roleId) {
  return request.get('/system/menu/permTree', { params: { roleId } });
}

// 提交：只收集权限节点里 checked 为 true 的 id
function collectCheckedIds(tree) {
  return tree
    .flatMap((menu) => menu.children ?? [])
    .filter((node) => node.type === 'PERMISSION' && node.checked)
    .map((node) => node.id);
}

await authPerm(roleId, collectCheckedIds(tree));
```

勾选 add/edit/delete 时请在 UI 上同步勾选 list，取消 list 时同步取消同组 add/edit/delete；若直接调 API 只传 edit 类 permissionId，后端仍会补全 list。

TS 类型（注意可选字段）：

```typescript
export interface PermTreeNode {
  id: number;
  nodeKey: string;
  name: string;
  type: 'MENU' | 'PERMISSION';
  permission?: string;      // 仅 PERMISSION 节点
  checked?: boolean;        // 仅 PERMISSION 节点
  children?: PermTreeNode[]; // 仅 MENU 节点
}
```

菜单层级预留了多级目录（`sys_menu.parent_id`），当前种子数据都是一级菜单。若后续出现子目录，`children` 里会同时混有 MENU 和 PERMISSION 节点，上面的 `flatMap` 需要改成递归遍历。

### 12.7 API 开放接口文档与证书密码（前端页面）

| 页面 | 路径 | 说明 |
|------|------|------|
| API 开放接口 | `/system/token` | Tab「Token 管理 \| 接口文档」；文档 Tab 调用 `GET /api/open/doc`，在线调试用 `fetch`（JWT 或 AK/SK，避免与 axios 拦截器冲突） |
| 我的证书 | `/system/cert/mine` | 审批通过且 `p12PasswordPending` 时显示「查看 P12 密码」；调用 `POST /system/cert/mine/reveal-password/{applyId}` 后弹窗展示，关闭后不可再次领取；前端会话内也会隐藏按钮 |
| 证书管理 | `/system/cert` | 审批签发成功后弹窗展示一次性 `p12Password`；下载的 bundle.zip 不含密码 |

---

## 13. 权限矩阵

### 13.1 测试账号（seed）

| 账号 | 密码 | 角色 |
|------|------|------|
| admin | 123456 | admin |
| user | 123456 | user |

### 13.2 角色权限（`02-insert-data.sql`）

| 权限 | admin | user |
|------|:-----:|:----:|
| system:user:list/add/edit/delete | ✅ | ❌ |
| system:role:list/add/edit/delete | ✅ | ❌ |
| api:token:list/add/get/delete | ✅ | ❌ |
| system:session:list/kick | ✅ | ✅ |
| system:session:manage | ✅ | ❌ |
| asset:vm:list | ✅ | ✅ |
| asset:vm:delete | ✅ | ❌ |
| asset:app:list | ✅ | ✅ |
| dashboard:view:all | ✅ | ❌ |

### 13.3 与 permission 无关的规则

| 规则 | 说明 |
|------|------|
| GET `/user/info` | 任意登录用户 |
| POST `/logout` | 任意登录用户，删除当前 Redis 会话并更新 DB 下线历史 |
| GET `/system/session` | 需 `system:session:list`；无 manage 时仅看自己 |
| GET `/system/session/history` | 需 `system:session:list`；无 manage 时仅看自己 |
| DELETE `/system/session/{sessionId}` | 需 `system:session:kick`；manage 可踢任意用户 |
| 登录 | 新登录自动吊销该用户全部旧会话（全用户单点） |
| GET `/asset/vm`、`/asset/app` | 任意登录用户，看**全部**数据 |
| PUT `/asset/vm`、`/asset/app` | 任意登录用户，但必须是 **owner** |
| GET `/dashboard/*?scope=mine` | 任意登录用户 |
| GET `/dashboard/*?scope=all` | 需 `dashboard:view:all` |
| 角色分配 add/edit/delete | 后端自动补全同模块 `list`（见 [4.2](#42-分配权限覆盖式)） |
| 系统管理菜单可见 | 需对应 `*:list`（用户/角色/任务/API Token/登录设备/证书） |
| 我的证书 | 需 `system:cert:mine` |
| 证书管理 | 需 `system:cert:list` |

---

## 14. 客户端证书

**Base path：** `/system/cert`（管理员）、`/system/cert/mine`（当前用户）  
**权限前缀：** `system:cert:*`

### 14.1 我的证书概览

```
GET /system/cert/mine
```

**权限：** `system:cert:mine`

**成功响应 `data`：** 当前用户签名证/加密证摘要、申请记录；申请项含 `downloadable`、`p12PasswordPending`（是否仍可领取 P12 密码），**不含**明文 `p12Password`。

### 14.2 申请证书

```
POST /system/cert/mine/apply
POST /system/cert/mine/reissue
```

**权限：** `system:cert:mine`

**请求体：**

```json
{ "applyReason": "首次申请客户端证书" }
```

**说明：** 同一用户仅允许 1 条 `pending` 申请；重发类型为 `reissue`，审批通过后会吊销旧证再签发新证。

### 14.3 下载证书包

```
GET /system/cert/mine/download/{applyId}
```

**权限：** `system:cert:mine`

**说明：** 仅 `approved` 且属于当前用户的申请可下载；返回 `bundle.zip`（含 `root-ca.crt`、`intermediate-ca.crt`、`sign.p12`、`encrypt.p12`、`README.txt`）。**证书包内不含 P12 密码**，密码须在本平台单独查看（见 [14.4](#144-查看-p12-密码一次性)）。

### 14.4 查看 P12 密码（一次性）

```
POST /system/cert/mine/reveal-password/{applyId}
```

**权限：** `system:cert:mine`

**说明：** 审批通过后，用户在「我的证书」页点击「查看 P12 密码」调用本接口。密码**仅返回一次**：服务端用 `LambdaUpdateWrapper` 显式 `SET p12_password = NULL`（**不可**用 `updateById(null)`，MyBatis-Plus 默认忽略 null 字段）；再次调用返回「P12 密码已查看，无法再次获取」。关闭弹窗后「查看 P12 密码」按钮消失（`p12PasswordPending` 变为 `false`）。`sign.p12` 与 `encrypt.p12` 使用同一密码。

**失败响应（业务 `code=500`）：**

| msg | 场景 |
|-----|------|
| P12 密码已查看，无法再次获取 | 已领取过，或并发重复请求 |
| 申请不存在或无权查看 | applyId 不属于当前用户 |
| 证书尚未签发 | 申请未 `approved` |

**成功响应 `data`：**

```json
{
  "applyId": 1,
  "p12Password": "Ab3xK9mN2pQr5sTv"
}
```

### 14.5 管理员 — 申请列表

```
GET /system/cert/apply?status=pending&userName=&pageNum=1&pageSize=10
```

**权限：** `system:cert:list`

### 14.6 管理员 — 证书列表

```
GET /system/cert?userName=&certType=sign|encrypt&status=0|1
```

**权限：** `system:cert:list`

### 14.7 审批通过（签发双证）

```
POST /system/cert/apply/{applyId}/approve
```

**权限：** `system:cert:approve`

**请求体：**

```json
{
  "subjectCn": "zhangsan",
  "subjectO": "personalDemo",
  "subjectOu": "user-1002",
  "validDays": 365
}
```

**成功响应 `data`：** 含一次性 `p12Password`（**仅本次审批响应返回**，列表接口不返回）。管理员弹窗展示后无法再次从平台获取；用户须在「我的证书」页自行领取（各看一次）。证书包下载文件内不含密码。

### 14.8 拒绝申请

```
POST /system/cert/apply/{applyId}/reject
```

**权限：** `system:cert:approve`

**请求体：** `{ "rejectReason": "信息不完整" }`

### 14.9 吊销证书

```
PUT /system/cert/{certId}/revoke
```

**权限：** `system:cert:revoke`

**说明：** 吊销后该证无法用于 `/login/cert`。

### 14.10 证书文件存储

签发后文件落盘于（可配置 `cert.storage-base-path`）：

```text
ca/client/users/{userId}/{applyId}/
  sign.key / sign.crt / sign.p12
  encrypt.key / encrypt.crt / encrypt.p12
  bundle.zip   # root-ca.crt + intermediate-ca.crt + sign/encrypt.p12 + README.txt（README 不含 P12 密码）
```

**P12 密码策略：**

| 环节 | 行为 |
|------|------|
| 审批通过 | 管理员响应中一次性返回；同时写入 `sys_cert_apply.p12_password` 供用户领取 |
| 用户领取 | `POST .../reveal-password/{applyId}` 返回一次后，`LambdaUpdateWrapper` 将 `p12_password` 置 NULL |
| 证书包 | ZIP / README **不包含**密码 |
| 列表/概览 | 仅 `p12PasswordPending: true/false`（`p12_password IS NOT NULL`），不回传明文 |

---

## 附录：接口速查

| 模块 | 方法 | 路径 |
|------|------|------|
| 认证 | POST | `/login` |
| 认证 | GET | `/login/cert`（8443，浏览器证书登录入口） |
| 认证 | POST | `/login/cert`（8443） |
| 认证 | GET | `/login/cert/check`（8443 诊断） |
| 认证 | GET | `/login/cert/debug`（8443 诊断，纯文本） |
| 认证 | POST | `/logout` |
| 认证 | GET | `/user/info` |
| 用户 | GET | `/system/user` |
| 用户 | POST | `/system/user` |
| 用户 | PUT | `/system/user` |
| 用户 | PUT | `/system/user/authRole` |
| 用户 | DELETE | `/system/user/{userId}` |
| 角色 | GET | `/system/role` |
| 角色 | GET | `/system/role/options` |
| 权限 | GET | `/system/permission/options` |
| 菜单 | GET | `/system/menu/permTree` |
| 登录设备 | GET | `/system/session` |
| 登录设备 | GET | `/system/session/history` |
| 登录设备 | DELETE | `/system/session/{sessionId}` |
| 证书 | GET | `/system/cert/mine` |
| 证书 | POST | `/system/cert/mine/apply` |
| 证书 | POST | `/system/cert/mine/reissue` |
| 证书 | GET | `/system/cert/mine/download/{applyId}` |
| 证书 | POST | `/system/cert/mine/reveal-password/{applyId}` |
| 证书 | GET | `/system/cert/apply` |
| 证书 | GET | `/system/cert` |
| 证书 | POST | `/system/cert/apply/{applyId}/approve` |
| 证书 | POST | `/system/cert/apply/{applyId}/reject` |
| 证书 | PUT | `/system/cert/{certId}/revoke` |
| API Token | GET | `/api/token` |
| API Token | GET | `/api/token/user/{userId}` |
| API Token | POST | `/api/token` |
| API Token | GET | `/api/token/grantOptions` |
| API Token | GET | `/api/open/doc` |
| API Token | DELETE | `/api/token/{accessKey}`（吊销） |
| 虚机 | GET | `/asset/vm` |
| 虚机 | PUT | `/asset/vm` |
| 应用 | GET | `/asset/app` |
| 应用 | PUT | `/asset/app` |
| 仪表盘 | GET | `/dashboard/overview` |
| 仪表盘 | GET | `/dashboard/kpi` |
| 仪表盘 | GET | `/dashboard/vm/by-lifecycle` |
| 仪表盘 | GET | `/dashboard/trend/vm` |

外部系统调用虚机/应用开放接口时，使用 AK/SK 请求头
`X-Access-Key`、`X-Secret-Key`；须 Token `asset` 含对应 grant（如 `vm:list`、`vm:edit`）。

完整自动化测试：`./scripts/test-all-api.sh`
