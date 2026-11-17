# personalDemo Backend

基于 **Spring Boot 2.6** 的后端服务：JWT + Shiro 认证、邮箱验证码自助注册、RBAC 用户/角色/权限、虚机与应用资产管理、仪表盘统计、Agent Runtime 签名代理。数据库默认 **人大金仓 KingbaseES**；本地可用 **SQLite** profile。

默认端口：`8080`（`dev` profile 见 `application-dev.yml`）

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
| 数据库 | KingbaseES（默认）/ SQLite（`sqlite` profile） | 8.6.0 / sqlite-jdbc |
| 缓存 | Redis + Spring Data Redis | 登录会话 / API Token / 注册验证码 |
| 邮件 | Spring Mail（SMTP） | 注册验证码（如 163 授权码） |
| 认证 | Apache Shiro + JWT | 1.13.0 / jjwt 0.11.5 |
| AOP | spring-boot-starter-aop | 操作日志 / 权限切面 |
| 构建 | Maven | 3.x |

---

## 功能概览

### 已实现（可联调）

| 模块 | 说明 |
|------|------|
| **认证** | 登录、JWT、Redis 在线会话、`GET /user/info` |
| **自助注册** | `POST /register/code`、`POST /register`（邮箱验证码，默认角色「普通用户」） |
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
│   ├── auth/                    # 登录、注册、会话、证书
│   ├── security/                # Shiro、JWT、PermissionAspect、Listener、AuthorizationCacheEvictor
│   ├── api/                     # AK/SK Token、开放接口文档
│   ├── system/user|role|permission/
│   ├── asset/                   # host/app + domain/application/port（P1 聚合试点）
│   ├── statistics/              # Dashboard
│   ├── quartz/                  # 定时任务（TaskRegistry + Quartz）
│   ├── common/                  # Log、LogAspect、operlog、AjaxResult
│   └── config/
└── src/main/resources/
    ├── application-sqlite.yml   # 本地无金仓：sqlite,dev
    ├── sql/
    │   ├── 01-create-tables.sql … 24-register-user-role.sql
    │   └── sqlite/              # SQLite schema + seed
    └── templates/mail/          # 注册验证码邮件模板
```

---

## 快速开始

### KingbaseES（默认）

1. JDK 1.8+、Maven 3.6+、KingbaseES、Redis、`lib/` 下 4 个 Kingbase JAR  
2. 按顺序执行 SQL（见下节；已有库需跑 `23-user-email.sql`、`24-register-user-role.sql`，下线旧模块再跑 `25-retire-legacy-modules.sql`）  
3. 复制 `application-local.example.yml` 为 `application-local.yml`（已被 git 忽略），填写数据源、`jwt.secret`（≥32 字符），以及 `spring.mail.username` / `password`（注册发信；也可用 `MAIL_USERNAME`、`MAIL_PASSWORD`）  
4. **Rebuild Project** 后运行 `BackendApplication`

### 本地 SQLite（无需 KingbaseES）

仍需 Redis。激活 profile `sqlite,dev`（数据文件默认 `backend/data/agent-platform.db`，启动时执行 `sql/sqlite/schema.sql` + `data.sql`）：

```bash
mvn spring-boot:run -Dspring-boot.run.profiles=sqlite,dev
```

自助注册仍依赖 SMTP；未配置 `MAIL_*` 时发验证码会失败。

**测试账号：**

| 用户 | 密码 | 说明 |
|------|------|------|
| admin | 123456 | 用户 / 角色 / 登录设备 / 证书管理全权限 |
| user | 123456 | 登录设备 list/kick、我的证书；**无** `system:user:*` / `system:role:*` |

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
12-role-crud-permissions.sql      # 已有库补充角色 CRUD 权限
09-fix-user-role-permissions.sql # user 角色被误加 system:user:* 时执行
21-login-session.sql              # 登录设备会话表与权限（已有库增量）
23-user-email.sql                 # sys_user.email + 唯一索引（自助注册）
24-register-user-role.sql         # 普通用户证书/设备权限与缺角色补齐
25-retire-legacy-modules.sql      # 下线仪表盘/资产/定时任务/API Token
03-verify.sql                     # 可选
```

历史增量脚本（`04`–`11`、`13`–`20` 等资产 / 仪表盘 / Job / Token）已由 `25` 退役，新环境不必再执行。

本地 SQLite 不跑上述 Kingbase 脚本，改用 `sql/sqlite/schema.sql` / `data.sql`（已含 email 等字段；启动时会清理遗留权限）。

### 角色权限（seed）

```text
admin: system:user:*, system:role:*, system:session:*, system:cert:*
user:  system:session:list/kick, system:cert:mine
```

---

## 认证与鉴权

- Header：`Authorization: Bearer <token>`
- `/login`、`/register`、`/register/code` 匿名；其余需 JWT（JWT 含 `jti`，绑定 `sys_login_session`）
- **自助注册：** 邮箱验证码存 Redis（默认 5 分钟有效、60 秒重发、最多 5 次错误）；成功后绑定配置项 `register.default-role`（默认「普通用户」）
- `POST /logout` 从 JWT 取 `jti`，删除 Redis 会话并将 DB 历史标为下线；`DELETE /system/session/{sessionId}` 使用同一吊销逻辑踢出设备
- **单点登录：** 新登录自动吊销该用户全部旧会话（`createSingleLoginSession`）
- **用户停用 / 删除：** `SysUserServiceImpl` 发布 `UserStatusChangedEvent`；Session、Cert、AuthCache Listener 在事务提交后级联吊销凭证（详见 [docs/SKELETON.md](./docs/SKELETON.md) §8.8）
- 无 permission → HTTP **403**，`msg: 无权限访问`
- 未登录 → HTTP **401**
- **角色分配：** 勾选某模块的 `add` / `edit` / `delete` 时，后端自动补全同模块 `list`，保证菜单与列表 API 可用（详见 [docs/API.md](./docs/API.md) §4.2）

| 场景 | 规则 |
|------|------|
| `/user/info` | 任意登录用户 |
| `/system/user/**` | 需 `system:user:*` |
| `/system/role/**`、`/system/menu/permTree` | 需 `system:role:*`（树接口另校验 admin） |
| `/system/session/**` | 需 `system:session:*` |
| `/system/cert/mine/**` | 需 `system:cert:mine` |
| `/system/cert/**` | 需 `system:cert:list/approve/revoke` |
| `/agent-runtime/**` | 登录即可（JWT / Cookie） |

**OptionVO：** 系统表返回 `{ id, label }`，入参传 id。详见 [docs/API.md](./docs/API.md)。

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
