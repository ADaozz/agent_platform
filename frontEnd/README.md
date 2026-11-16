# frontEnd

Agent Platform 网页端：Vue 3 + Vite + TypeScript + Tailwind。开发服务器将 `/api` 代理到 Spring Boot 后台。

## 环境

- Node.js 20+（建议与仓库锁文件一致）
- 推荐：VS Code + [Vue (Official)](https://marketplace.visualstudio.com/items?itemName=Vue.volar)（关闭 Vetur）

## 命令

```sh
npm install
npm run dev      # 开发；代理目标可用 VITE_PROXY_TARGET
npm run build    # vue-tsc + Vite 生产构建
```

## 目录要点

| 路径 | 说明 |
| --- | --- |
| `src/views/LoginView.vue` | 登录 / 注册入口；宽屏加载 3D 背景 |
| `src/components/LoginScene.vue` | 走廊背景 + 悬浮 GLB 模块（three.js 按需分块） |
| `src/assets/login/` | `login-bg.webp`、`data-module.glb` |
| `src/agent-platform/` | Agent 对话、文件与文档预览宿主界面 |
| `src/api/` | 后端 REST 封装（含 `/register`、`/register/code`） |
| `接口文档.md` | 与后端 API 对齐的前端对接说明 |

登录页 3D 场景的光照、交互与性能策略见仓库文档 [docs/login-scene/README.md](../docs/login-scene/README.md)。

## 登录页行为摘要

- **宽屏（≥901px）**：动态加载 three，渲染工业走廊 LDR 背景与数据模块；走廊灯带风格 PMREM 环境光 + 本地光；鼠标跟随轻微倾斜（约 30fps）；原生 MSAA。
- **窄屏**：不加载 3D，仅用 CSS 背景图。
- **注册**：邮箱验证码自助注册（依赖后端 SMTP 与 Redis）。
- **`prefers-reduced-motion`**：关闭空闲动画，仍可根据指针重绘姿态。
