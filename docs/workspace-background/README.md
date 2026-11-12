# PR #6：纯 CSS 工作区背景

参考本轮提供的 `78507.jpg`，将 Agent 对话区域绘制为暖白科研档案 / 碳黑工业控制台。图片只用于设计参考，没有将其或其他 PNG、WebP、SVG 图片作为背景资源加入产品。

## 实际修改

| 文件（相对 frontEnd/src） | 修改 |
| --- | --- |
| components/WorkspaceBackdrop.vue | 新增纯装饰组件；只有模板与 CSS，没有 script、Canvas、图片 URL、定时器或绘制代码 |
| agent-platform/AgentPlatform.vue | 在原 main 内增加一个可选 backdrop 插槽，其余模板和脚本不变 |
| views/AgentChatView.vue | 通过插槽提供背景，复用已有主题；用 CSS 对齐现有内容边界、操作栏及预览面板边界 |
| styles/agent-workspace.css | 移除旧的全区域点阵背景；保留已有主题、组件尺寸和交互样式 |

现有 Logo、菜单选中橙条、侧栏悬停行为及品牌三色反射代码均未修改。没有修改后端、路由、状态、API、输入框、消息区或文件预览的业务逻辑，没有新增依赖。

## 视觉与适配

- 浅色使用现有 Warm Ivory 主背景，浅金色圆弧与暖橙光晕；深色使用 Carbon Black、低亮度暖灰圆弧与暗橙光晕。
- 四周轨道由 radial / repeating-radial-gradient、圆形遮罩和等宽高伪元素构成，使用 cqi、百分比、clamp 和 aspect-ratio，不会将圆形拉伸成椭圆。粗环锚定左下，主要细环锚定右上；中心保持留白。
- 定位十字由径向及水平/垂直线性渐变组成，斜向工业条纹使用 repeating-linear-gradient，角点使用径向渐变，三色标记使用分段线性渐变。没有图片数据 URI。
- 页头左侧为 `DEEP AGENT`，右侧为 `AGENT WORKSPACE / SYSTEM ONLINE`；页脚左侧为 `DEEP AGENT`，右侧为 `INTELLIGENCE / EXECUTION / WORKSPACE`。保留分割线、三色标记及斜纹，不给装饰三色标记添加反射动画。
- 背景是 main 内的零高度 sticky 装饰层，绘制区域绝对定位，位于业务内容下方。已有会话操作栏存在时，装饰页头位于其下方；薄页脚贴合可见对话区域底部，不为背景增加业务布局的留白或改变控件位置。
- 背景宽度来自原对话 main 的实际宽度，不估算侧栏状态。桌面预览打开时，随 main 收窄；移动端预览按原有 700px 断点切为上下分屏，背景在底部预览面板上边缘结束。600px 断点只同步已有内容边距，没有改变业务响应式规则。
- 铭牌使用可收缩 flex、min-width: 0、单行省略及局部 overflow 裁切。极窄时省略文字，保持边界。装饰层为 aria-hidden、inert、pointer-events: none，不进入键盘焦点，也不处理点击或滚动。

## 验证结果

基线：`6e50b8b`。真实 Chromium + Playwright，使用一致的受控 API 数据。

- 1440×1000、900×900、390×844、320×740，各检查浅色、深色。
- 每组实际执行对话显示、侧栏展开、预览打开、预览打开时展开侧栏、预览关闭、新建对话首页，共 48 组前后截图和几何对照。
- 除新增装饰元素外，原有元素数量、边界框、尺寸与圆角全部一致；页面横向宽度与基线一致，浏览器无页面错误。
- 背景宽度与 main 实际宽度一致，装饰页脚底边与绘制区域底边一致。桌面背景右边缘对齐预览左边缘；移动端背景下边缘对齐预览上边缘。
- 正常动画模式额外检查桌面/移动 × 浅色/深色四种组合：侧栏过渡期间逐帧检查背景与 main 宽度，最大差值为 0；圆弧宽高一致，深色调色变量正确，背景没有图片 URL。
- 长对话实际滚动及预览开关时，背景与铭牌位置保持固定；输入框点击、键盘输入正常，装饰 inert 状态正确。
- `npm run build`：通过，包含 `vue-tsc --build` 类型检查与 Vite 构建。
- `npm run test:e2e:office`：通过。
- `node --test agent-runtime/tests/{conversation,outputFiles,office-review,documents}.test.mjs`：34 项通过，0 失败。
- `git diff --check`：通过。

### 已知基线问题与验证范围

320px 屏幕展开 248px 侧栏时，原应用顶栏的按钮区域导致 document 宽度为 348px，即已有 28px 横向溢出。修改前后完全一致；新背景及铭牌被裁切在实际对话容器内，没有增加页面横向宽度。此次遵守“不改变现有布局和控件尺寸”的限制，没有改动顶栏。390px、900px、1440px 测试没有页面横向溢出。

本次使用受控 API 数据验证前端，未进行真实后端登录、模型执行或文件生成联调。

## 截图

| 状态 | 浅色 | 深色 |
| --- | --- | --- |
| 对话首页 | [截图](1440-light-home.png) | [截图](1440-dark-home.png) |
| 有内容会话 | [截图](1440-light-conversation.png) | [截图](1440-dark-conversation.png) |
| 桌面预览打开 | [截图](1440-light-preview.png) | [截图](1440-dark-preview.png) |
| 390px 预览打开 | [截图](390-light-preview.png) | [截图](390-dark-preview.png) |

其他状态：[侧栏与预览同时打开](1440-light-preview-sidebar.png) · [900px 预览](900-dark-preview.png) · [320px 预览](320-light-preview.png) · [320px 展开侧栏的基线限制](320-light-preview-sidebar.png)
