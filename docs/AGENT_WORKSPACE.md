# Agent Platform 架构与部署

## 定位

Spring Boot 后台（`backend/`）是**主产品及业务后端**：复用现有 Spring Boot 2.6 + Shiro/JWT + KingbaseES + Redis 用户认证、角色授权、证书和在线登录设备管理。资产管理、虚机、应用、仪表盘、Job、API Token **从主界面菜单和路由移除**；原 Java 实现暂不物理删除，以免破坏既有数据和认证依赖。

保留的页面：

- `/agent`：Agent 工作台，所有已登录用户可使用
- `/system/user`：用户管理（沿用 `system:user:list`）
- `/system/role`：角色管理（沿用 `system:role:list`）
- `/system/session`：登录设备（沿用 `system:session:list`）
- `/system/cert/mine`：我的证书（沿用 `system:cert:mine`）
- `/system/cert`：证书管理（沿用 `system:cert:list`）

侧栏折叠状态在浏览器持久化。Agent 页面复用 ITAM 的 CSS 变量、Tailwind v4 组件风格和主体布局，不引入第二套全局导航。

## 架构

```text
Browser / Vue 3
  | JWT Authorization: Bearer <user JWT>
  v
Spring Boot (backend/, :8080)
  | Shiro UserRealm: JWT + jti + Redis session + active user
  | RBAC: admin/user
  | /agent-runtime/api/** => signed internal reverse proxy
  v
FastAPI (agent-runtime/, :8090, loopback)
  | short-lived HMAC signed identity (user ID, role, method, raw path, query)
  | Session owner enforced on EVERY session-scoped HTTP request
  | User-filtered session listing, owner assigned on creation
  v
Native AgentRunner (platform_app/agent_core)
  | session-scoped Sandbox + checkpoint + SSE events
  | files, tools, document/presentation features
```

**后端通信采用 HMAC 签名而非把浏览器 JWT 交给 Agent。** Spring Boot 负责校验 JWT、登录会话是否已经吊销、用户是否停用，并从 Shiro Principal 读取可信 userId。签名包含短时有效时间戳、userId、role、HTTP 方法、原始路径和查询串；Python 验证后才允许访问资源。禁止浏览器自己传 `X-Agent-User-Id` 绕过认证；代理会覆盖这些字段。

Python 服务当前仍保留原始 SQLite 平台数据目录存储模型与 checkpoint，但 ITAM 模式下会话绑定 `owner_user_id` 并按用户过滤。旧的无 owner 会话不自动开放给任何人。现有每 Thread 的 Workspace、文件、沙箱及 Agent checkpoint 持续复用。后续可进一步迁移到统一数据服务，不应在迁移时直接共享用户私有文件。

## 启动

### 1. 配置相同的签名密钥

设置两个进程的环境变量（值必须一致，建议随机 32 字节以上，不要入 Git）。

```bash
export AGENT_RUNTIME_SHARED_SECRET='replace-with-a-random-secret-of-at-least-32-bytes'
export ITAM_RUNTIME_SHARED_SECRET="$AGENT_RUNTIME_SHARED_SECRET"
```

生产环境请用独立的 Secret Manager，以上示例仅展示变量名。

### 2. 启动 Python Agent Runtime

需安装 Python 3.12+、Bubblewrap、Office（可选）等依赖，参见 [agent-runtime/README.md](../agent-runtime/README.md)。

```bash
cd agent-runtime
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -r docx-ooxml-skill/requirements.txt -r pptx-ooxml-skill/requirements.txt
export ITAM_RUNTIME_SHARED_SECRET="$AGENT_RUNTIME_SHARED_SECRET"
export PLATFORM_DATA_DIR=.platform-itam
.venv/bin/uvicorn platform_app.main:app --host 127.0.0.1 --port 8090
```

`127.0.0.1` 只适合同一网络命名空间；跨容器部署请使用只允许 Spring Boot 访问的私有服务网络，**禁止向公网直接暴露 Python 端口**。

### 3. 启动 Spring Boot

仍需配置 KingbaseES、Redis、JWT、证书路径等既有依赖。另设置：

```bash
export AGENT_RUNTIME_URL='http://127.0.0.1:8090'
export AGENT_RUNTIME_SHARED_SECRET='<与 Python 相同的随机密钥>'
```

Spring Boot 启动后登录 ITAM，访问 `/agent`。开发模式仍使用 `frontEnd/vite.config.ts` 的 `/api` 代理；Vue 的 Agent API 从 `/api/agent-runtime/api/**` 走统一后端，不直接连接 Python。

## 用户和管理员边界

| 功能 | user | admin |
|---|---|---|
| Agent 对话、个人会话、文件 | 可 | 可（仅自己的） |
| 沙箱、文件、事件与审批 | 按 Thread 且用户隔离 | 按 Thread 且用户隔离 |
| 模型/全局 Agent 设置修改 | 禁止 | 允许 |
| 用户、角色、设备、证书 | 继续沿用现有权限码 | 继续沿用现有权限码 |
| full-access 沙箱 | 禁止（多用户模式） | 禁止（多用户模式） |

**重要：** 当前 Agent Runtime 的全局模型和工具配置仍由平台存储，只有管理员能修改，但配置会影响所有新用户会话；普通用户只可选择现有模型。正式启用时应确保旧 SQLite 中的模型配置与数据目录权限正确。

## 最低验收

1. 旧 ITAM 的 login/cert、logout、用户、角色、设备和证书操作不回归。
2. user 与 admin 登录后均能使用 `/agent`，但 user 无法 PUT `/api/models` 或 `/api/settings`。
3. A 创建会话、上传文件；B 的会话列表不包含 A 的记录，直接请求 A 的 ID 返回 404，包括 SSE、日志、文件和 Office 路由。
4. JWT 过期、登出或踢掉登录设备后，新 Agent HTTP 请求返回 401。
5. 空签名、过期签名、篡改 userId/role/path/query/method 均不允许进入 Python Runtime。
6. 不能通过 `full-access` 新建会话或修改正在运行的沙箱；restricted 隔离继续由 AgentRunner 执行。
7. 执行长任务时 SSE 持续输出工具日志；任务中断和刷新可重放 journal。
8. DOCX/PPTX 输出可下载，并可在右侧面板按页预览。

## 当前范围

Agent 对话页（`frontEnd/src/agent-platform/`）复用 Agent Runtime 的网页界面，包含聊天、SSE 执行时间线、工具审批、文件上传下载、全局文件、DOCX/PPTX 按页预览与通用文件预览。浏览器访问文件和预览图片时使用只读 HttpOnly Cookie，由 Spring Boot 校验后签名转发。

Agent 工具、Skill 与 MCP 配置在多用户模式下由服务端统一管理，前端不开放修改；用户只能在「平台设置 → 模型配置」中使用全局模型或维护私人模型。
