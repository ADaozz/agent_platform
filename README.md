# Agent Platform

多用户 Agent 平台：Spring Boot 负责用户认证、角色权限、证书登录与登录设备管理，Vue 3 提供统一网页界面，Python Agent Runtime（FastAPI + LangGraph / deepagents）负责 Agent 执行、沙箱隔离与 DOCX / PPTX 文档生成和预览。

## 架构

```text
浏览器（Vue 3，frontEnd/）
  │  JWT（Authorization: Bearer）；预览图片与下载使用只读 HttpOnly Cookie
  ▼
Spring Boot（backend/，:8080）
  │  Shiro + JWT + Redis 会话校验，RBAC（admin / user）
  │  /agent-runtime/api/** → 附加 HMAC 签名身份后反向代理
  ▼
Agent Runtime（agent-runtime/，FastAPI，:8090，仅本机或内网）
  │  校验签名，会话按用户隔离
  ▼
Agent 执行引擎：Bubblewrap 沙箱、checkpoint、SSE 事件流、DOCX / PPTX Skill
```

浏览器不直接访问 Python 服务。Spring Boot 校验登录状态后，用共享密钥对用户 ID、角色、时间戳、HTTP 方法、路径和查询串签名，Python 端验证通过才处理请求。

## 目录

| 路径 | 内容 |
| --- | --- |
| `backend/` | Spring Boot 2.6 后台：Shiro + JWT、KingbaseES、Redis、用户/角色/证书/登录设备管理、Agent Runtime 签名代理 |
| `frontEnd/` | Vue 3 + Vite + Tailwind 前端；`src/agent-platform/` 为 Agent 对话、文件与文档预览界面 |
| `agent-runtime/` | Python Agent Runtime、内置执行引擎、DOCX / PPTX Skill 与测试，说明见 [agent-runtime/README.md](agent-runtime/README.md) |
| `docs/` | 架构、部署与验收说明，见 [AGENT_WORKSPACE.md](docs/AGENT_WORKSPACE.md) |
| `ca/`、`ca_test/` | 证书登录使用的 CA 与服务端证书（仅公开证书，私钥不入库） |

## 功能

- **账号与权限**：账号密码登录与客户端证书登录，用户、角色、登录设备（可踢下线）、证书签发与管理。
- **Agent 对话**：多轮会话、流式执行时间线、工具审批、暂停/继续/取消、运行中追加指令；历史对话可删除。
- **文件**：附件上传，会话产出文件下载与预览，跨会话的全局文件列表（按类型显示图标）。
- **文档生成**：DOCX 支持公式、原生图表、题注与交叉引用、目录、复杂表格、图文排版、页眉页脚，预览按页浏览、只更新变化的页面；PPTX 提供风格化生成、原生图表与公式和逐页预览。
- **模型配置**：管理员维护全局模型；普通用户使用全局模型，并可配置加密保存的私人模型。Agent 工具与 Skill 由服务端统一管理。
- **界面**：中英文切换、白天/黑夜模式（默认黑夜）、可折叠侧栏。

## 快速开始

### 1. 共享签名密钥

两个服务使用同一个随机密钥（至少 32 字节），不要提交到仓库：

```bash
export AGENT_RUNTIME_SHARED_SECRET="$(openssl rand -base64 48)"
export ITAM_RUNTIME_SHARED_SECRET="$AGENT_RUNTIME_SHARED_SECRET"
```

### 2. Agent Runtime

需要 Linux / WSL2、Python 3.12+、Bubblewrap；正式渲染 DOCX / PPTX 预览还需 LibreOffice 与中文字体。

```bash
cd agent-runtime
python3 -m venv .venv
.venv/bin/pip install -r requirements.lock
.venv/bin/pip install -r docx-ooxml-skill/requirements.txt -r pptx-ooxml-skill/requirements.txt
PLATFORM_DATA_DIR=.platform-itam .venv/bin/uvicorn platform_app.main:app --host 127.0.0.1 --port 8090
```

### 3. Spring Boot 后台

需要 JDK 8+、Maven、KingbaseES 与 Redis。

1. 按 [backend/README.md](backend/README.md) 初始化数据库。
2. 复制 `backend/src/main/resources/application-local.example.yml` 为 `application-local.yml`（已被忽略，不入库），填写数据源和 JWT 密钥；也可使用环境变量 `DB_URL`、`DB_USERNAME`、`DB_PASSWORD`、`JWT_SECRET`、`JWT_API_SECRET`。
3. 设置 `AGENT_RUNTIME_URL`（默认 `http://127.0.0.1:8090`）和上面的 `AGENT_RUNTIME_SHARED_SECRET`，然后启动 `BackendApplication`。

### 4. 前端

```bash
cd frontEnd
npm install
npm run dev
```

开发服务器把 `/api` 代理到后台，目标地址可用环境变量 `VITE_PROXY_TARGET` 指定。生产构建使用 `npm run build`，由 nginx 等代理 `/api`。

## 安全说明

- Python Agent Runtime 只能监听本机或仅后台可访问的私有网络，不要暴露到公网。
- 数据库密码、JWT 密钥、签名密钥、私钥与证书包均不入库，相应文件已在 `.gitignore` 中忽略。
- 多用户模式下禁止 `full-access` 沙箱，每个会话的文件、命令与 Skill 快照相互隔离。

## 测试

```bash
# Agent Runtime
cd agent-runtime
.venv/bin/pip install pytest httpx
.venv/bin/python -m pytest -q
PYTHONPATH=. .venv/bin/python -m pytest -q docx-ooxml-skill/tests pptx-ooxml-skill/tests

# 前端类型检查与构建
cd frontEnd && npm run build
```

后台接口测试脚本与数据库说明见 [backend/README.md](backend/README.md)。
