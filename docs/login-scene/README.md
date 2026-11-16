# 登录页 3D 场景

宽屏登录页左侧主视觉：工业走廊照片背景 + 悬浮的数据卡带 GLB 模块。实现集中在 [`frontEnd/src/components/LoginScene.vue`](../../frontEnd/src/components/LoginScene.vue)，由 [`LoginView.vue`](../../frontEnd/src/views/LoginView.vue) 在 `min-width: 901px` 时挂载。

## 资源

| 文件 | 用途 |
| --- | --- |
| `frontEnd/src/assets/login/login-bg.webp` | 走廊 LDR 背景（CSS 回退 + `scene.background`） |
| `frontEnd/src/assets/login/data-module.glb` | meshopt 压缩的悬浮模块 |

无独立 HDR；IBL 由代码内自定义走廊灯带场景经 `PMREMGenerator.fromScene` 生成。

## 光照

曾使用 Three.js `RoomEnvironment`（摄影棚）作 `scene.environment`，与走廊背景不是同一光场，模块反射像棚拍贴片。

当前方案：

1. `createCorridorEnvironment`：深色腔体、顶/侧冷白 emissive 灯带、底部弱红 + 少量 PointLight，仅用于烘焙 PMREM，不进入主场景。
2. `scene.background` 仍为走廊 WebP（cover 裁切）。
3. 主场景本地光：冷白 Directional（顶光）、冷色 rim、右下弱红 PointLight。
4. 模块下方极淡软边圆形接触阴影（CanvasTexture plane），不做 shadowMap。

模型基础偏航约 `+0.5` rad，正面朝右面向用户。

## 交互

- 非 OrbitControls：在 `window` 上监听 `pointermove`，平滑倾斜 `pivot`（不受 `.login-hero` 遮挡）。
- 空闲摆动幅度低于指针贡献，避免「写了交互却感觉不到」。
- `prefers-reduced-motion`：停 rAF 循环；指针移动时节流重绘静止帧。

## 性能

| 策略 | 说明 |
| --- | --- |
| 无后处理 | 去掉 EffectComposer / Bokeh（原 DOF 几乎不可见） |
| 原生 MSAA | `antialias: true` |
| DPR | 默认 ≤1.25；弱设备 ≤1 |
| 帧率 | 约 30fps |
| 灯光 | 主场景 3 盏 |
| 弱设备 | `hardwareConcurrency` / `deviceMemory` / Save-Data 时降低 env 强度与浮动 |
| 分块 | three 与 GLTF/meshopt 动态 `import`，画布淡入前由 CSS 背景顶替 |
| 生命周期 | 标签页隐藏停帧；卸载 dispose 几何/材质/纹理/renderer |

## 验收建议

- 宽屏：模块高光呈灯带状冷白，与走廊顶光/地面红大致同向；移动鼠标倾斜可感知。
- 窄屏：不请求 GLB / three 分块。
- 降低系统动画偏好后：无空闲浮动，指针仍可轻微转向。
