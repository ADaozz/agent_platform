# Agent Platform 视觉收敛验收

本次只调整前端视觉：碳黑工业控制台、暖白科研档案、信号橙交互，以及现有几何图案的颜色层级。保留全部布局、尺寸、间距、圆角、响应式断点、DOM 层级、业务逻辑及功能动画。没有增加依赖，没有修改后端或共享 Agent 工作区实现。

## 实际修改文件

| 文件（相对 frontEnd/src） | 修改摘要 |
| --- | --- |
| assets/main.css | 收敛全局品牌与明暗主题变量；通用装饰条、行悬停改为橙色；去除普通蓝紫色装饰 |
| styles/agent-workspace.css | 将共享工作区语义变量关联到全局变量，删除重复配色；列表、文件、弹窗及档案标题的装饰统一橙色 |
| layouts/AppLayout.vue | 保留品牌三色条，仅在其内部增加反射伪元素；导航标记改为橙色 |
| components/BrandMark.vue | 保留 SVG 路径及外形，指令符与图标底条统一信号橙 |
| components/PageHeader.vue | 标题卡片底部三色装饰改为橙色结构线 |
| components/BaseDrawer.vue | 抽屉装饰条改为橙色，位置与尺寸不变 |
| components/AppIcon.vue | 通用图标端点与转角采用 square / miter；保留原路径、线宽与尺寸 |
| components/OrbitDial.vue | 装饰参考弧、星迹改为信号橙；保留分段标识、动画及仪表几何 |
| components/SpaceField.vue | 星迹用品牌橙，薄雾用暖灰，网格用暖白；动画不变 |
| views/LoginView.vue | 恒定深色主视觉协调到 Carbon Black、Warm Ivory 及 Signal Orange |

已检查 `agent-platform/theme.css`：它提供共享工作区变量契约，仍保持原样，由现有宿主覆盖层映射颜色。已检查 `icons/index.ts`：保留原有工业图标路径与语义映射。BaseModal 沿用全局 `.tri-bar`，无需再增加局部覆盖。

## 关键变量

| 变量 | 当前值 / 用途 |
| --- | --- |
| --color-carbon | #181818，深色主背景 |
| --color-panel | #242320，深色面板 |
| --color-ivory | #F5EDDC，浅色主背景、深色文字 |
| --color-signal | #F36B18，主操作与装饰 |
| --color-tri-red | #C84940，品牌、危险操作及错误状态色源 |
| --color-tri-yellow | #DFA93C，品牌及警告状态色源 |
| --color-tri-green | #83A695，品牌及完成状态色源 |
| --color-warm-gray | #958A78，深色辅助文字及结构色源 |
| --color-primary | 深色用 Signal Orange；浅色用 70% Signal Orange 与 30% Carbon Black 混合，保证小号橙色文字对比度 |
| --brand-tricolor | 原三段等分渐变；仅 `.rail-tri` 使用 |

浅色面板、边框、错误/警告/成功文字保留同色系的明暗变体，以保证可读性。工作区的 `--page`、`--surface`、`--border`、`--text-*`、`--signal` 等直接引用宿主变量，不再单独维护一整套相同 HEX 值。现有低对比点阵、扫描线、斜纹、同心轨道继续使用，没有新增噪声图层或霓虹光效。

## 品牌反射

`.rail-tri::after` 为绝对定位、不可交互的纯 CSS 伪元素。18px 宽的径向渐变内包含约 7px 的柔和高光，以 10 秒周期及对称缓动水平往返。首尾位置相同，往返端点速度趋零；不改变透明度、不闪烁、不脉冲。原色条使用 `overflow: hidden` 裁切，宽度、3px 高度、位置及圆角均保持原值；底层三色分区不变。`prefers-reduced-motion: reduce` 时明确设置 `animation: none`，保留静态微弱反射。

反射仅绑定 `.rail-tri`，不影响标题文字，也不影响侧栏悬停展开、延迟收起或菜单切换。OrbitDial 未接入真实状态，原三色装饰参考弧通过 CSS 改为单色，原有分段数据和动画全部保留。

## 验证

运行环境：Node 24.22.1、仓库锁文件依赖、真实 Chromium + Playwright。基线来自提交 `2946236`。页面使用一致的受控 API 数据与字体；静态截图启用减少动态效果，品牌动画另在正常动态设置下检查。

- `npm ci`：完成，无依赖或锁文件变更。
- `npm run build`：通过，包含 `vue-tsc --build` 类型检查及 Vite 生产构建。
- `npm run test:e2e:office`：通过。覆盖独立审查组、页码/区域定位、运行/空闲状态委派、重试与错误、旧版本隔离、PPTX 高亮/忽略操作。
- `node --test agent-runtime/tests/{conversation,outputFiles,office-review,documents}.test.mjs`：34 项通过，0 失败。只运行相关前端数据处理测试，未修改运行时代码。
- 宿主 Office 面板在深色/浅色 × 桌面 1600×1000 / 移动 390×844 四种组合下重复现有浏览器测试：全部通过。
- 登录、Agent 首页、模型配置、用户管理、角色管理、登录设备管理、我的证书、证书管理：深色/浅色 × 桌面 1440×1000 / 移动 390×844，共 32 组前后对照，边界框、尺寸、圆角与元素层级一致。另采集四种侧栏展开状态，检查展开 248px、收起 64px。
- DOCX/PPTX 共 8 组宿主面板对照：边界框、尺寸、圆角及渲染层级一致。
- 有内容会话、Markdown 文件预览：明暗主题 × 桌面/移动端共 8 组前后对照（统一滚动位置），边界框、尺寸、圆角与渲染层级一致；会话切换、预览打开/关闭及工具执行完成反馈通过。
- 品牌反射四种组合检查：10 秒周期、首尾一致、对称往返、裁切、3px 高度、无鼠标命中、reduced-motion 停止、侧栏收起均通过。
- 8 个改动的 Vue 组件：排除注释后，script/script setup 与基线完全一致。
- `git diff --check`：通过。

这些是受控数据下的前端验证。管理页覆盖空列表状态，模型配置及会话使用固定内容；Office 面板使用仓库现有文档渲染图片和审查记录。未启动真实后端，未验证真实登录、保存配置、用户/证书写入或外部模型执行，不将截图测试视为后端端到端联调。

## 前后截图

每张对照图左侧 BEFORE、右侧 AFTER；只并排拼接并添加标签，没有修饰页面像素。截图中的时钟自然推进。

| 页面 | 对照图 |
| --- | --- |
| 登录 / 深色 | [查看](login-dark.png) |
| Agent 首页与展开侧栏 / 深色 | [查看](workspace-dark.png) |
| 模型配置 / 浅色 | [查看](models-light.png) |
| Agent 首页 / 移动浅色 | [查看](workspace-mobile.png) |
| 有内容会话 / 深色 | [查看](conversation-dark.png) |
| 文件预览 / 浅色 | [查看](file-preview-light.png) |
| DOCX 审查 / 深色 | [查看](docx-dark.png) |
| PPTX 审查 / 浅色 | [查看](pptx-light.png) |
