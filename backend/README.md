# personalDemo Backend

基于 **Spring Boot 2.6** 的后端服务：JWT + Shiro 认证、RBAC 用户/角色/权限、虚机与应用资产管理、仪表盘统计。数据库 **人大金仓 KingbaseES**。

默认端口：`8080`

**前端对接文档：** [docs/API.md](./docs/API.md)  
**骨架复用文档：** [docs/SKELETON.md](./docs/SKELETON.md)（**Spring Boot Backend Skeleton v1.0**）  
**解耦与依赖总览：** [docs/DDD-DECOUPLING.md](./docs/DDD-DECOUPLING.md)（P0 用户事件 + P1 Asset 聚合）

---

## 目录

- [技术栈](#技术栈)
- [功能概览](#功能概览)
- [项目结构](#项目结构)
- [快速开始](#快速开始)
- [数据库初始化](#数据库初始化)
- [认证与鉴权](#认证与鉴权)
- [接口测试](#接口测试)
- [常见问题](#常见问题)
- [开发说明](#开发说明)

---

## 技术栈

| 类别 | 技术 | 版本 |
|------|------|------|
| 语言 | Java | 1.8 |
| 框架 | Spring Boot | 2.6.13 |
| ORM | MyBatis-Plus | 3.5.5 |
| 数据库 | KingbaseES | 8.6.0 |
| 缓存 | Redis + Spring Data Redis | 登录会话 / API Token |
| 认证 | Apache Shiro + JWT | 1.13.0 / jjwt 0.11.5 |
| AOP | spring-boot-starter-aop | 操作日志 / 权限切面 |
| 构建 | Maven | 3.x |

---

## 功能概览

### 已实现（可联调）

| 模块 | 说明 |
|------|------|
| **认证** | 登录、JWT、Redis 在线会话、`GET /user/info` |
| **用户管理** | 列表/详情/新增/修改/删除/分配角色 |
| **虚机 / 应用** | 全员 list；仅 owner 可 update；生命周期单向流转 |
| **角色/权限** | 角色 CRUD、权限列表、选项接口 |
| **仪表盘** | `scope=mine\|all`；VO 对齐 ECharts |
| **API Token** | 创建、列表、吊销、Redis 鉴权缓存；**开放接口动态文档**（`/api/open/doc`） |
| **定时任务** | 扫描注册、Quartz 调度、管理接口 |
| **操作日志** | `@Log` 注解 + 控制台输出（不落库） |
| **权限校验** | `@RequiresPermissions` + `PermissionAspect` |
| **操作日志** | `@Log` + `LogAspect` → `sys_oper_log` 异步落库 |
| **权限缓存** | RBAC 变更后 `AuthorizationCacheEvictor` 失效 Shiro 授权缓存 |

### 待完善

| 模块 | 说明 |
|------|------|
| 定时任务日志 | 执行日志查询接口 |
| 操作日志 | 落库 |

---

## 项目结构

```
backend/
├── docs/API.md                  # 前端对接 API 文档 ⭐
├── docs/DDD-DECOUPLING.md       # Impl 依赖矩阵、解耦路线图、改后总览图
├── docs/DEVELOPMENT.md          # 后端开发详解
├── docs/SKELETON.md             # 骨架复用 Checklist
├── scripts/
│   └── test-all-api.sh          # 全量接口（含 AK/SK 开放接口）
├── src/main/java/org/example/backend/
│   ├── auth/                    # 登录、会话、证书
│   ├── security/                # Shiro、JWT、PermissionAspect、Listener、AuthorizationCacheEvictor
│   ├── api/                     # AK/SK Token、开放接口文档
│   ├── system/user|role|permission/
│   ├── asset/                   # host/app + domain/application/port（P1 聚合试点）
│   ├── statistics/              # Dashboard
│   ├── quartz/                  # 定时任务（TaskRegistry + Quartz）
│   ├── common/                  # Log、LogAspect、operlog、AjaxResult
│   └── config/
└── src/main/resources/sql/
    ├── 01-create-tables.sql
    ├── 02-insert-data.sql
    ├── 04~08-*.sql
    └── 09-fix-user-role-permissions.sql  # 纠正 user 角色误分配权限
```

---

## 快速开始

1. JDK 1.8+、Maven 3.6+、KingbaseES、`lib/` 下 4 个 Kingbase JAR  
2. 按顺序执行 SQL（见下节）  
3. 复制 `application-local.example.yml` 为 `application-local.yml`（已被 git 忽略），填写数据源与 `jwt.secret` / `jwt.api.secret`（≥32 字符）；也可用环境变量 `DB_URL`、`DB_USERNAME`、`DB_PASSWORD`、`JWT_SECRET`、`JWT_API_SECRET`  
4. **Rebuild Project** 后运行 `BackendApplication`

**测试账号：**

| 用户 | 密码 | 说明 |
|------|------|------|
| admin | 123456 | 用户管理、仪表盘 all、资产 owner 虚机 |
| user | 123456 | 资产 list、登录设备 list/kick、dashboard mine；**无** `system:user:*` |

```bash
curl --noproxy '*' -X POST http://172.21.16.1:8080/login \
  -H "Content-Type: application/json" \
  -d '{"userName":"admin","passWord":"123456"}'
```

> WSL 访问 Windows 后端用 `172.21.16.1:8080`，勿用 `127.0.0.1`；curl 建议加 `--noproxy '*'` 避免走代理 502。

---

## 数据库初始化

### 执行顺序

```text
01-create-tables.sql
02-insert-data.sql
04-asset-tables.sql
05-insert-asset-data.sql      # 可选样例
06-asset-permissions.sql      # 已有库增量
07-scaffold-tables.sql
10-api-token-ak-sk.sql       # 已有库启用 AK/SK Token 的增量脚本
11-api-token-permissions.sql # 已有库补充 API Token 管理权限
12-role-crud-permissions.sql # 已有库补充角色 CRUD 权限
08-dashboard-permissions.sql  # 已有库增量
09-fix-user-role-permissions.sql  # user 角色被误加 system:user:* 时执行
21-login-session.sql              # 登录设备会话表与权限（已有库增量）
03-verify.sql                 # 可选
```

### 角色权限（seed）

```text
admin: system:user:*, system:role:*, api:token:*, system:session:*, asset:*, dashboard:view:all
user:  asset:vm:list, asset:vm:edit, asset:app:list, asset:app:edit, system:session:list/kick
```

---

## 认证与鉴权

- Header：`Authorization: Bearer <token>`
- `/login` 匿名；其余需 JWT（JWT 含 `jti`，绑定 `sys_login_session`）
- `POST /logout` 从 JWT 取 `jti`，删除 Redis 会话并将 DB 历史标为下线；`DELETE /system/session/{sessionId}` 使用同一吊销逻辑踢出设备
- **单点登录：** 新登录自动吊销该用户全部旧会话（`createSingleLoginSession`）
- **用户停用 / 删除：** `SysUserServiceImpl` 发布 `UserStatusChangedEvent`；Session、ApiToken、Cert、AuthCache 四个 Listener 在事务提交后级联吊销凭证（详见 [docs/SKELETON.md](./docs/SKELETON.md) §8.8）
- 无 permission → HTTP **403**，`msg: 无权限访问`
- 未登录 → HTTP **401**
- **角色分配：** 勾选某模块的 `add` / `edit` / `delete` 时，后端自动补全同模块 `list`，保证菜单与列表 API 可用（详见 [docs/API.md](./docs/API.md) §4.2）
- 外部业务查询也支持 AK/SK：
  `X-Access-Key` + `X-Secret-Key`
- AK/SK 仅允许 GET `/asset/vm`、`/asset/app`，并且 Token 必须授权对应
  `asset`（`vm` 或 `app`）；写操作仍必须使用登录 JWT

| 场景 | 规则 |
|------|------|
| `/user/info` | 任意登录用户 |
| `/system/user/**` | 需 `system:user:*` |
| GET `/asset/vm`、`/asset/app` | 登录即可，看全部 |
| PUT `/asset/vm`、`/asset/app` | 登录 + 必须为虚机 **owner** |
| GET `/dashboard?scope=mine` | 登录即可 |
| GET `/dashboard?scope=all` | 需 `dashboard:view:all` |

**OptionVO：** 系统表返回 `{ id, label }`，入参传 id。详见 [docs/API.md](./docs/API.md)。

### AK/SK 开放接口

创建 API Token 后，外部系统使用响应中的 `accessKey` 和 `secretKey` 查询已授权业务资源：

```http
X-Access-Key: ak-xxxxxxxx
X-Secret-Key: eyJhbGciOiJIUzI1NiJ9...
```

当前仅支持只读查询：

```bash
curl --noproxy '*' \
  -H "X-Access-Key: ak-xxxxxxxx" \
  -H "X-Secret-Key: eyJhbGciOiJIUzI1NiJ9..." \
  "http://172.21.16.1:8080/asset/vm?pageNum=1&pageSize=10"
```

Token 创建时通过 `asset` 绑定业务资源，目前支持 `vm` 和 `app`。AK/SK
只能使用 GET，不能调用资产修改接口。完整字段和鉴权流程见
[docs/API.md](./docs/API.md)。

---

## 接口测试

```bash
chmod +x scripts/test-all-api.sh

# 全量（包含认证、用户、角色、资产、仪表盘和 AK/SK 开放接口）
BASE_URL=http://172.21.16.1:8080 ./scripts/test-all-api.sh

# 使用 docs/API-test.txt 中的 AK/SK 测试开放接口
BASE_URL=http://172.21.16.1:8080 \
  RUN_API_TOKEN_TESTS=0 \
  ./scripts/test-all-api.sh

VERBOSE=1 ./scripts/test-all-api.sh   # 打印响应 body
```

---

## 常见问题

### user 能访问 /system/user

数据库 `sys_role_permission` 中 role_id=2 被误加了 `system:user:list`。执行 `09-fix-user-role-permissions.sql` 后 user 重新登录。

### 403 / 401

- 403：角色无该 permission 或未重新登录  
- 401：token 缺失或过期
- AK/SK 401：检查 `docs/API-test.txt` 中的密钥是否过期、是否匹配数据库
- AK/SK 403：检查 Token 的 `asset` 是否包含目标资源；外部 Token 目前只允许 GET

### 修改虚机报「无权修改该虚机」

仅 `owner_user_id = 当前用户` 可改；测试虚机 owner 为 admin(1001)。

### Kingbase `sys_user` 冲突

自定义 SQL JOIN 用户表时用 `public.sys_user`，避免与系统视图同名。

### 重启后 /system/user 仍 404

需 **Rebuild Project** 再启动，确认日志有 `Mapped "{[/system/user]"`。

---

## 开发说明

```text
Controller  → @Valid DTO、AjaxResult、@RequiresPermissions、@Log
Service     → 门面或业务逻辑；Asset 写路径委托 ApplicationService
Domain      → 聚合不变量（Asset：VmHost / VmLifecycle）
GET 列表    → QueryDTO + PageResultVO { total, rows }
```

### 待办

- 操作日志落库（当前仅控制台）  

### 相关入口

| 模块 | 文件 |
|------|------|
| API 文档 | `docs/API.md` |
| 解耦总览 | `docs/DDD-DECOUPLING.md` |
| 开发详解 | `docs/DEVELOPMENT.md` |
| API 测试凭证 | `docs/API-test.txt` |
| API 测试脚本 | `scripts/test-all-api.sh` |
| 用户 | `system/user/controller/SysUserController.java` |
| 用户状态事件 | `system/user/event/UserStatusChangedEvent.java` |
| 停用级联 Listener | `auth/session/listener/`、`api/listener/`、`auth/cert/listener/`、`security/listener/` |
| VmHost 聚合 | `asset/host/domain/model/VmHost.java` |
| Asset 写/读 | `asset/host/application/`、`asset/app/application/` |
| 仪表盘 | `statistics/controller/DashboardController.java` |
| 权限切面 | `security/aspect/PermissionAspect.java` |
| 授权缓存失效 | `security/cache/AuthorizationCacheEvictor.java` |
| 操作日志 | `common/aspect/LogAspect.java`、`common/operlog/` |

---

## License

内部项目 / 个人演示用途。
