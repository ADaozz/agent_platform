# Agent Platform 前端

Vue 3 + Vite + Tailwind 的多用户 Agent 工作台。

## 当前页面

- Agent 对话及文件管理（`src/agent-platform/`），含 DOCX / PPTX 预览与审查
- 模型配置
- 用户管理、角色管理、登录设备管理
- 我的证书、证书管理
- 登录页及共享导航布局

路由统一定义在 `src/router/index.ts`，登录和权限仍沿用已有后端接口。

## 开发

```sh
npm ci
npm run dev
```

```sh
npm run build
npm run test:e2e:office
```

旧 ITAM 的虚拟机、应用、定时任务、数据统计和资产 API Token 前端页面已移除。清理仅限前端，不改变后端 API、数据结构或权限逻辑。现有 Agent 工作区及权限/证书页面保留。
