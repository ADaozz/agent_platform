<script setup lang="ts">
/**
 * 登录页 3D 背景：走廊背景图 + 悬浮的数据卡带模块。
 * three 及其扩展按需动态加载，打成单独分块；加载完成并画出第一帧后画布才淡入，
 * 在此之前由外层的 CSS 背景图顶替——淡入时背景由锐变虚，形成一次“对焦”。
 *
 * 融合手段：背景景深 + 压暗、轮廓光晕、浮尘、
 * 跟随模块的 HUD 框。全部为几何/着色器，无后处理。
 * 性能策略：原生 MSAA、DPR≤2（弱设备≤1.5）、约 30fps。
 * 观察窗关掉 transmission（改半透明），避免透射 RT 把正面字/磁带抹糊。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type * as THREE from 'three'
import bgUrl from '@/assets/login/login-bg.webp'
import modelUrl from '@/assets/login/data-module.glb?url'

const host = ref<HTMLDivElement>()
const ready = ref(false)
/** 模块在视口中的包围框（px），HUD 框按它定位 */
const hud = ref({ x: 0, y: 0, w: 0, h: 0 })

let teardown: (() => void) | null = null
let unmounted = false

/** 模型中心在视口中的位置（0–1），落在左侧主视觉区偏右的上半部分 */
const ANCHOR = { x: 0.36, y: 0.4 }
const CAMERA_DISTANCE = 6
/** 装饰场景无需 60fps；30fps 足够，显著降低 GPU/电池占用 */
const FRAME_MS = 1000 / 30
/** 模块身后轮廓光晕的基准不透明度 */
const HALO = 0.14

/**
 * 走廊灯带风格的 IBL 源场景（仅用于 PMREM，不进入主场景）。
 * 深色腔体 + 细亮灯带（金属要硬高光）+ 底部弱红。
 * 灯带用中性偏暖白，避免冰蓝把古铜漂青；不做大面积暖面光（会抹掉金属对比）。
 */
function createCorridorEnvironment(T: typeof THREE): THREE.Scene {
  const env = new T.Scene()
  env.name = 'CorridorLightEnvironment'

  const boxGeo = new T.BoxGeometry(1, 1, 1)
  boxGeo.deleteAttribute('uv')

  // 近黑腔体：反射暗部沉下去，亮带才跳得出来
  const cavity = new T.Mesh(
    boxGeo,
    new T.MeshStandardMaterial({
      color: 0x0c0b0a,
      roughness: 1,
      metalness: 0,
      side: T.BackSide,
    }),
  )
  cavity.scale.set(12, 6, 18)
  env.add(cavity)

  const wallMat = new T.MeshStandardMaterial({
    color: 0x1e1a17,
    roughness: 0.85,
    metalness: 0.35,
  })
  const leftWall = new T.Mesh(boxGeo, wallMat)
  leftWall.position.set(-4.2, 0, 0)
  leftWall.scale.set(0.35, 5.2, 16)
  const rightWall = new T.Mesh(boxGeo, wallMat)
  rightWall.position.set(4.2, 0, 0)
  rightWall.scale.set(0.35, 5.2, 16)
  env.add(leftWall, rightWall)

  const floor = new T.Mesh(
    boxGeo,
    new T.MeshStandardMaterial({ color: 0x040506, roughness: 0.92, metalness: 0.2 }),
  )
  floor.position.set(0, -2.85, 0)
  floor.scale.set(10, 0.08, 16)
  env.add(floor)

  function addGlow(
    emissive: number,
    intensity: number,
    x: number,
    y: number,
    z: number,
    sx: number,
    sy: number,
    sz: number,
  ) {
    const mat = new T.MeshStandardMaterial({
      color: 0xffffff,
      emissive,
      emissiveIntensity: intensity,
      roughness: 1,
      metalness: 0,
    })
    const strip = new T.Mesh(boxGeo, mat)
    strip.position.set(x, y, z)
    strip.scale.set(sx, sy, sz)
    env.add(strip)
  }
  // 高对比灯带 / 面板：金属表面要能清楚映出形状
  addGlow(0xfff4e8, 22, 0, 2.85, 0, 0.4, 0.1, 14)
  addGlow(0xfff4e8, 16, -1.6, 2.85, 0, 0.2, 0.07, 12)
  addGlow(0xfff4e8, 16, 1.6, 2.85, 0, 0.2, 0.07, 12)
  addGlow(0xeef3ff, 14, -3.9, 1.2, 0, 0.07, 0.14, 10)
  addGlow(0xeef3ff, 14, 3.9, 1.2, 0, 0.07, 0.14, 10)
  addGlow(0xfff6ee, 18, 0, 2.0, 5.8, 3.5, 0.12, 0.1)
  addGlow(0xfff6ee, 14, -2.6, 0.4, 5.2, 0.1, 2.2, 0.1)
  addGlow(0xfff6ee, 14, 2.6, 0.4, 5.2, 0.1, 2.2, 0.1)
  addGlow(0xffffff, 12, 0, -0.2, -6.2, 5.5, 2.4, 0.12)

  // 大面积柔光箱：给金属包边一段宽而柔的渐变，给观察窗一片可读的倒影
  // 偏在左上与右下，不正对镜头：倒影只占窗面一角，随模块摆动滑过，而不是整片泛白
  addGlow(0xfff0e0, 2.4, -4.6, 3.0, 5.2, 2.6, 2.0, 0.1)
  addGlow(0xf3ece4, 1.1, 4.4, -1.8, 4.6, 1.8, 1.8, 0.1)

  const floorGlow = new T.Mesh(
    boxGeo,
    new T.MeshStandardMaterial({
      color: 0x120808,
      emissive: 0xc42822,
      emissiveIntensity: 1.1,
      roughness: 1,
      metalness: 0,
    }),
  )
  floorGlow.position.set(0, -2.7, 2)
  floorGlow.scale.set(3.5, 0.05, 4)
  env.add(floorGlow)

  const fill = new T.PointLight(0xfff2e6, 24, 20, 2)
  fill.position.set(0, 2.4, 2)
  const sideFill = new T.PointLight(0xe8eef8, 12, 14, 2)
  sideFill.position.set(-3.2, 1.4, -1)
  const redFill = new T.PointLight(0xc42822, 5, 10, 2)
  redFill.position.set(1.5, -2.2, 3)
  env.add(fill, sideFill, redFill)

  return env
}

/**
 * 景深背景：只把模块身后的一片虚化，其余保持清晰——走廊的结构线条仍然可读，
 * 模块落在一块柔焦区上而不是整张糊掉的图前。整体略压暗、去一点饱和。
 * 虚化层略放大绘制，避免模糊把画布外的透明像素卷进边缘。不支持 ctx.filter 时退化为原图。
 */
function createFocusedBackground(T: typeof THREE, image: CanvasImageSource & { width: number; height: number }) {
  const scale = Math.min(1, 1800 / image.width)
  const canvas = document.createElement('canvas')
  const w = (canvas.width = Math.round(image.width * scale))
  const h = (canvas.height = Math.round(image.height * scale))
  const ctx = canvas.getContext('2d')!
  const grade = 'brightness(0.8) saturate(0.86) contrast(1.05)'
  ctx.filter = grade
  ctx.drawImage(image, 0, 0, w, h)

  const soft = document.createElement('canvas')
  soft.width = w
  soft.height = h
  const sctx = soft.getContext('2d')!
  const blur = Math.max(2, w * 0.0042)
  const pad = blur * 3
  sctx.filter = `blur(${blur}px) ${grade} brightness(0.9)`
  sctx.drawImage(image, -pad, -pad, w + pad * 2, h + pad * 2)
  // 柔焦区：以模块锚点为中心的椭圆，向外渐变回清晰
  sctx.filter = 'none'
  sctx.globalCompositeOperation = 'destination-in'
  const cx = ANCHOR.x * w
  const cy = (ANCHOR.y + 0.04) * h
  const radius = w * 0.34
  sctx.translate(cx, cy)
  sctx.scale(1, 0.82)
  const mask = sctx.createRadialGradient(0, 0, radius * 0.35, 0, 0, radius)
  mask.addColorStop(0, 'rgba(0,0,0,1)')
  mask.addColorStop(1, 'rgba(0,0,0,0)')
  sctx.fillStyle = mask
  sctx.fillRect(-w, -h, w * 2, h * 2)

  ctx.filter = 'none'
  ctx.drawImage(soft, 0, 0)
  const tex = new T.CanvasTexture(canvas)
  tex.colorSpace = T.SRGBColorSpace
  return tex
}

function canvasTexture(T: typeof THREE, size: number, draw: (ctx: CanvasRenderingContext2D, c: number) => void) {
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  draw(ctx, size / 2)
  const tex = new T.CanvasTexture(canvas)
  tex.colorSpace = T.SRGBColorSpace
  return tex
}

/** 画面平均色（线性空间），用作雾色 */
function averageColor(T: typeof THREE, canvas: HTMLCanvasElement) {
  const probe = document.createElement('canvas')
  probe.width = probe.height = 8
  const ctx = probe.getContext('2d')!
  ctx.drawImage(canvas, 0, 0, 8, 8)
  const data = ctx.getImageData(0, 0, 8, 8).data
  let r = 0, g = 0, b = 0
  for (let i = 0; i < data.length; i += 4) {
    r += data[i]!
    g += data[i + 1]!
    b += data[i + 2]!
  }
  const n = (data.length / 4) * 255
  return new T.Color().setRGB(r / n, g / n, b / n, T.SRGBColorSpace)
}

/** 柔边径向光斑：轮廓光晕与浮尘共用 */
function createGlowTexture(T: typeof THREE, size = 128) {
  return canvasTexture(T, size, (ctx, c) => {
    const g = ctx.createRadialGradient(c, c, 0, c, c, c)
    g.addColorStop(0, 'rgba(255,255,255,1)')
    g.addColorStop(0.35, 'rgba(255,255,255,0.4)')
    g.addColorStop(1, 'rgba(255,255,255,0)')
    ctx.fillStyle = g
    ctx.fillRect(0, 0, size, size)
  })
}

function isLiteDevice(): boolean {
  const cores = navigator.hardwareConcurrency || 4
  const mem = (navigator as Navigator & { deviceMemory?: number }).deviceMemory
  const saveData = (navigator as Navigator & { connection?: { saveData?: boolean } }).connection?.saveData
  return !!saveData || cores <= 4 || (typeof mem === 'number' && mem <= 4)
}

async function setup(el: HTMLDivElement) {
  const [T, { GLTFLoader }, { MeshoptDecoder }] = await Promise.all([
    import('three'),
    import('three/addons/loaders/GLTFLoader.js'),
    import('three/addons/libs/meshopt_decoder.module.js'),
  ])
  if (unmounted) return

  let renderer: THREE.WebGLRenderer
  try {
    renderer = new T.WebGLRenderer({
      antialias: true,
      alpha: false,
      powerPreference: 'high-performance',
      stencil: false,
      depth: true,
    })
  } catch {
    return
  }
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const lite = isLiteDevice()
  // 正面文字/磁带需要可读：普通设备跟到 2×，弱设备 1.5×；再靠 MSAA 压金属边
  const pixelRatio = Math.min(window.devicePixelRatio || 1, lite ? 1.5 : 2)
  renderer.setPixelRatio(pixelRatio)
  renderer.toneMapping = T.NeutralToneMapping
  renderer.toneMappingExposure = 0.92
  const maxAnisotropy = Math.min(16, renderer.capabilities.getMaxAnisotropy())

  const scene = new T.Scene()
  const camera = new T.PerspectiveCamera(28, 1, 0.1, 100)
  camera.position.set(0, 0, CAMERA_DISTANCE)

  const corridorEnv = createCorridorEnvironment(T)
  const pmrem = new T.PMREMGenerator(renderer)
  const envTexture = pmrem.fromScene(corridorEnv, 0.04).texture
  pmrem.dispose()
  const envGeos = new Set<THREE.BufferGeometry>()
  const envMats = new Set<THREE.Material>()
  corridorEnv.traverse((obj) => {
    const mesh = obj as THREE.Mesh
    if (!mesh.isMesh) return
    envGeos.add(mesh.geometry)
    for (const material of ([] as THREE.Material[]).concat(mesh.material)) envMats.add(material)
  })
  envGeos.forEach((g) => g.dispose())
  envMats.forEach((m) => m.dispose())
  scene.environment = envTexture
  // IBL 主导表面反射；本地光再收，避免漫射把反射冲掉
  scene.environmentIntensity = lite ? 1.0 : 1.4

  const key = new T.DirectionalLight(0xfff0e0, 1.25)
  key.position.set(-1.5, 5, 4)
  // 轮廓光取走廊灯带的暖白，不再用冷蓝：与背景同一套光
  const rim = new T.DirectionalLight(0xffe9d2, 0.9)
  rim.position.set(3.5, 1.5, -4)
  // 掠射高光：专门擦过古铜包边上沿，金属边才有亮边
  const bevel = new T.DirectionalLight(0xfff8f0, lite ? 1.6 : 2.4)
  bevel.position.set(-3.4, 5.2, 2.2)
  const glow = new T.PointLight(0xc42822, 2.4, 9, 2)
  glow.position.set(2.2, -2, 2.4)
  scene.add(key, rim, bevel, glow)

  const loader = new GLTFLoader()
  loader.setMeshoptDecoder(MeshoptDecoder)
  let loaded: [THREE.Texture, { scene: THREE.Group }]
  try {
    loaded = await Promise.all([new T.TextureLoader().loadAsync(bgUrl), loader.loadAsync(modelUrl)])
  } catch {
    envTexture.dispose()
    renderer.dispose()
    return
  }
  const [bgTexture, gltf] = loaded
  const model = gltf.scene
  const tuned = new Set<THREE.Material>()
  // 关掉不必要的矩阵每帧更新与视锥外开销预期；单模型仍保留 frustumCulled
  model.traverse((obj) => {
    const mesh = obj as THREE.Mesh
    if (!mesh.isMesh) return
    mesh.castShadow = false
    mesh.receiveShadow = false
    // 同心磁带层几何频率过高，屏幕上易出摩尔纹：隔层隐藏，保留卷绕感
    const layerMatch = mesh.name.match(/磁带层_(\d+)/)
    if (layerMatch && Number(layerMatch[1]) % 2 === 0) {
      mesh.visible = false
      return
    }
    const mats = ([] as THREE.Material[]).concat(mesh.material)
    for (const m of mats) {
      // 材质被多个网格共用：只调一次，否则粗糙度会被反复相乘
      if (tuned.has(m)) continue
      tuned.add(m)
      const std = m as THREE.MeshStandardMaterial
      if (std.isMeshStandardMaterial) {
        const name = std.name || ''
        const tape = /磁带|卷绕|卷带|卷盘/.test(name)
        const metal =
          !tape && ((std.metalness ?? 0) >= 0.45 || /古铜|香槟|钢|金手指|阳极|金属|螺丝/.test(name))
        if (tape) {
          // 压法线/高光/环境反射，减轻同心纹与屏幕采样打架
          std.envMapIntensity = lite ? 0.45 : 0.55
          std.roughness = Math.min(1, Math.max(std.roughness ?? 0.5, 0.62))
          std.metalness = Math.min(std.metalness ?? 0, 0.02)
          if (std.normalMap) std.normalScale.set(0.06, 0.06)
          if ('specularIntensity' in std) (std as THREE.MeshPhysicalMaterial).specularIntensity = 0.25
        } else {
          // 金属强环境反射；有 roughnessMap 时也要压 factor，否则贴图粗糙度会把倒影糊掉
          std.envMapIntensity = metal ? (lite ? 1.7 : 2.35) : lite ? 1.15 : 1.45
          if (metal) {
            std.metalness = Math.min(1, Math.max(std.metalness ?? 0.8, 0.92))
            // 缎面金属：既映出灯带的硬高光，也留一段柔和的漫射渐变，而不是镜面黑
            std.roughness = Math.min(0.3, Math.max(0.14, (std.roughness ?? 0.4) * 0.6))
          } else if (typeof std.roughness === 'number') {
            std.roughness = Math.max(0.12, std.roughness * 0.9)
          }
        }
        // 吃场景雾：模块被走廊的空气“罩”住，而不是贴在背景上
        std.fog = true
      }
      // 透射亚克力观察窗：transmission 走低分 RT，会把窗后几何字/磁带抹成一片
      const phys = m as THREE.MeshPhysicalMaterial
      if (phys.isMeshPhysicalMaterial && phys.transmission > 0) {
        phys.transmission = 0
        phys.transparent = true
        // 烟灰亚克力：底色近黑，只负责把窗后压暗；亮度全部来自表面反射
        phys.opacity = 0.3
        phys.color.set(0x0b0c0d)
        phys.depthWrite = false
        phys.roughness = 0.06
        phys.metalness = 0
        phys.envMapIntensity = lite ? 1.3 : 1.8
        phys.specularIntensity = 1
        phys.ior = 1.52
        phys.side = T.FrontSide
        phys.clearcoat = 0
        phys.fog = false
        // 普通半透明会把高光一起乘上不透明度，玻璃反射因此发灰。
        // 这里让反射不受透明度衰减：有反射的地方提高 alpha，并按新 alpha 还原亮度。
        phys.onBeforeCompile = (shader) => {
          shader.fragmentShader = shader.fragmentShader.replace(
            '#include <opaque_fragment>',
            `{
              vec3 glassSpec = reflectedLight.directSpecular + reflectedLight.indirectSpecular;
              #ifdef USE_CLEARCOAT
                glassSpec += clearcoatSpecularDirect + clearcoatSpecularIndirect;
              #endif
              glassSpec = min(glassSpec, outgoingLight);
              float a0 = diffuseColor.a;
              float a1 = clamp(a0 + max(glassSpec.r, max(glassSpec.g, glassSpec.b)) * (1.0 - a0), a0, 1.0);
              outgoingLight = ((outgoingLight - glassSpec) * a0 + glassSpec) / a1;
              diffuseColor.a = a1;
            }
            #include <opaque_fragment>`,
          )
        }
        phys.customProgramCacheKey = () => 'login-glass'
        phys.needsUpdate = true
      }
      const tapeMat = /磁带|卷绕|卷带|卷盘/.test((m as THREE.Material).name || '')
      for (const value of Object.values(m)) {
        const tex = value as THREE.Texture
        if (!tex || !tex.isTexture) continue
        // 磁带贴图降低各向异性，避免把细密法线/细节锐到出纹
        tex.anisotropy = tapeMat ? Math.min(2, maxAnisotropy) : maxAnisotropy
        tex.generateMipmaps = true
        tex.minFilter = T.LinearMipmapLinearFilter
        tex.magFilter = T.LinearFilter
        tex.needsUpdate = true
      }
    }
  })

  // 壳内遮蔽：没有实时阴影时方向光会直接照进卡带内部，卷盘和机构亮得像贴图。
  // 观察窗后的零件单独克隆材质并压暗直射光与环境反射，近似光追下壳体自遮挡的效果；
  // 只留一点高光，转动时仍能读出金属轮毂与磁带的轮廓。
  const INTERIOR = /卷盘|磁带|卷带|内部|磁头|导带|压带|轮毂|前窗内侧/
  const occluded = new Map<THREE.Material, THREE.Material>()
  // 淡琥珀色腔内灯（视空间位置每帧更新）
  const lampUniforms = {
    uLampView: { value: new T.Vector3() },
    uLampColor: { value: new T.Color(0xffa040).multiplyScalar(lite ? 1.5 : 1.9) },
    uLampRadius: { value: 1 },
  }
  function occlude(source: THREE.Material) {
    let copy = occluded.get(source)
    if (!copy) {
      copy = source.clone()
      const std = copy as THREE.MeshStandardMaterial
      if (std.isMeshStandardMaterial) {
        std.envMapIntensity *= 0.22
        std.onBeforeCompile = (shader) => {
          Object.assign(shader.uniforms, lampUniforms)
          shader.fragmentShader = shader.fragmentShader
            .replace(
              '#include <common>',
              '#include <common>\nuniform vec3 uLampView;\nuniform vec3 uLampColor;\nuniform float uLampRadius;',
            )
            .replace(
              '#include <opaque_fragment>',
              `outgoingLight *= 0.3;
              {
                // 腔内小灯：只在壳内零件上生效，距离衰减得快，照亮一小片卷盘和磁带
                vec3 toLamp = uLampView + vViewPosition;
                float dist = length(toLamp);
                float fall = pow(clamp(1.0 - dist / uLampRadius, 0.0, 1.0), 2.0);
                float wrap = 0.35 + 0.65 * max(dot(normalize(normal), toLamp / max(dist, 1e-4)), 0.0);
                outgoingLight += (diffuseColor.rgb * 0.85 + 0.05) * uLampColor * fall * wrap;
              }
              #include <opaque_fragment>`,
            )
        }
        std.customProgramCacheKey = () => 'login-occluded'
      }
      occluded.set(source, copy)
    }
    return copy
  }
  // scene.environment 不读材质的 envMapIntensity：显式挂上环境贴图，金属/玻璃/磁带的强度才各自生效。
  // 放在贴图过滤设置之后，避免改到 PMREM 贴图的采样参数。
  for (const m of tuned) {
    const std = m as THREE.MeshStandardMaterial
    if (std.isMeshStandardMaterial) std.envMap = envTexture
  }
  model.traverse((obj) => {
    const mesh = obj as THREE.Mesh
    if (!mesh.isMesh || !INTERIOR.test(mesh.name) || /观察窗/.test(mesh.name)) return
    mesh.material = Array.isArray(mesh.material) ? mesh.material.map(occlude) : occlude(mesh.material)
  })

  let focusTexture: THREE.CanvasTexture | undefined
  function disposeScene() {
    scene.traverse((obj) => {
      const mesh = obj as THREE.Mesh
      if (!mesh.isMesh) return
      mesh.geometry.dispose()
      for (const material of ([] as THREE.Material[]).concat(mesh.material)) {
        for (const value of Object.values(material)) {
          if (value && (value as THREE.Texture).isTexture) (value as THREE.Texture).dispose()
        }
        material.dispose()
      }
    })
    focusTexture?.dispose()
    bgTexture.dispose()
    envTexture.dispose()
  }
  if (unmounted) {
    disposeScene()
    renderer.dispose()
    return
  }
  el.appendChild(renderer.domElement)
  focusTexture = createFocusedBackground(T, bgTexture.image as HTMLImageElement)
  focusTexture.generateMipmaps = false
  focusTexture.minFilter = T.LinearFilter
  focusTexture.magFilter = T.LinearFilter
  scene.background = focusTexture
  // 取背景的平均色做空气色：雾把模块的暗部抬到与走廊同一灰度，光晕也用它而不是信号橙
  const air = averageColor(T, focusTexture.image as HTMLCanvasElement)
  scene.fog = new T.Fog(air, CAMERA_DISTANCE * 0.55, CAMERA_DISTANCE * 5)

  const pivot = new T.Group()
  const box = new T.Box3().setFromObject(model)
  const size = box.getSize(new T.Vector3())
  model.position.sub(box.getCenter(new T.Vector3()))
  pivot.add(model)

  // 光晕与浮尘不随模块倾摆：单独一组，只跟随位置与缩放
  const stage = new T.Group()
  const additive = (map: THREE.Texture, color: THREE.ColorRepresentation, opacity: number) =>
    new T.MeshBasicMaterial({
      map,
      color,
      opacity,
      transparent: true,
      depthWrite: false,
      blending: T.AdditiveBlending,
      side: T.DoubleSide,
      toneMapped: false,
      fog: false,
    })

  const glowTex = createGlowTexture(T)
  // 轮廓光晕：把模块从背景里“托”出来
  const halo = new T.Mesh(new T.PlaneGeometry(1, 1), additive(glowTex, air.clone().lerp(new T.Color(0xffe2c4), 0.5), HALO))
  halo.scale.set(size.x * 2.6, size.y * 2.4, 1)
  halo.position.set(0, size.y * 0.05, -size.z * 2.2)
  halo.renderOrder = -2
  stage.add(halo)

  // 浮尘：深度错落，缓慢上浮
  const dustCount = lite ? 70 : 160
  const dustBox = new T.Vector3(size.x * 3.2, size.y * 3.2, size.z * 6)
  const dustSeed = new Float32Array(dustCount * 4)
  const dustPositions = new Float32Array(dustCount * 3)
  for (let i = 0; i < dustCount; i++) {
    dustSeed.set([Math.random(), Math.random(), Math.random(), Math.random()], i * 4)
  }
  const dustGeo = new T.BufferGeometry()
  dustGeo.setAttribute('position', new T.BufferAttribute(dustPositions, 3))
  const dust = new T.Points(
    dustGeo,
    new T.PointsMaterial({
      map: glowTex,
      color: 0xffd2a8,
      size: 0.045,
      sizeAttenuation: true,
      transparent: true,
      opacity: 0.45,
      depthWrite: false,
      blending: T.AdditiveBlending,
      toneMapped: false,
      fog: false,
    }),
  )
  dust.frustumCulled = false
  stage.add(dust)
  scene.add(stage)

  // 灯位在两卷盘之间偏左下，半径只够到一侧卷盘：照出一部分，其余留在暗里
  const lamp = new T.Object3D()
  lamp.position.set(-size.x * 0.12, -size.y * 0.1, size.z * 0.12)
  pivot.add(lamp)
  const lampBase = lampUniforms.uLampColor.value.clone()

  function animateStage(t: number) {
    const breath = reduceMotion ? 1 : 0.85 + Math.sin(t * 1.3) * 0.15
    lamp.getWorldPosition(lampUniforms.uLampView.value).applyMatrix4(camera.matrixWorldInverse)
    lampUniforms.uLampRadius.value = size.x * 0.46 * pivot.scale.x
    // 极轻的明暗起伏，像老设备里的指示灯
    lampUniforms.uLampColor.value.copy(lampBase).multiplyScalar(reduceMotion ? 1 : 0.92 + Math.sin(t * 2.1) * 0.08)
    ;(halo.material as THREE.MeshBasicMaterial).opacity = HALO * breath
    for (let i = 0; i < dustCount; i++) {
      const [a, b, c, d] = [dustSeed[i * 4]!, dustSeed[i * 4 + 1]!, dustSeed[i * 4 + 2]!, dustSeed[i * 4 + 3]!]
      const rise = reduceMotion ? 0 : t * (0.015 + d * 0.03)
      dustPositions[i * 3] = (a - 0.5) * dustBox.x + (reduceMotion ? 0 : Math.sin(t * 0.4 + d * 9) * size.x * 0.04)
      dustPositions[i * 3 + 1] = (((b + rise) % 1) - 0.5) * dustBox.y
      dustPositions[i * 3 + 2] = (c - 0.5) * dustBox.z
    }
    dustGeo.attributes.position!.needsUpdate = true
  }

  // 跟随模块的局部高光：正面包边一抹暖白，侧棱一点冷闪
  const faceSpec = new T.SpotLight(0xfff2e2, lite ? 8 : 13, size.x * 6, Math.PI / 6, 0.62, 1.6)
  faceSpec.position.set(-size.x * 0.55, size.y * 0.75, size.z * 1.55)
  faceSpec.target.position.set(0, size.y * 0.05, size.z * 0.35)
  const edgeSpec = new T.SpotLight(0xfff0e4, lite ? 4 : 7, size.x * 5, Math.PI / 7, 0.7, 1.8)
  edgeSpec.position.set(size.x * 1.15, size.y * 0.15, size.z * 1.1)
  edgeSpec.target.position.set(size.x * 0.35, 0, 0)
  pivot.add(faceSpec, faceSpec.target, edgeSpec, edgeSpec.target)

  scene.add(pivot)

  const base = new T.Vector3()
  function layout() {
    const w = el.clientWidth
    const h = el.clientHeight
    if (!w || !h) return
    renderer.setSize(w, h, false)
    camera.aspect = w / h
    camera.updateProjectionMatrix()

    const bg = focusTexture!
    const img = bg.image as { width: number; height: number }
    const imageAspect = img.width / img.height
    const viewAspect = w / h
    if (viewAspect > imageAspect) bg.repeat.set(1, imageAspect / viewAspect)
    else bg.repeat.set(viewAspect / imageAspect, 1)
    bg.offset.set((1 - bg.repeat.x) / 2, (1 - bg.repeat.y) / 2)

    const viewH = 2 * CAMERA_DISTANCE * Math.tan(T.MathUtils.degToRad(camera.fov / 2))
    const viewW = viewH * camera.aspect
    base.set((ANCHOR.x - 0.5) * viewW, (0.5 - ANCHOR.y) * viewH, 0)
    // 略放大：PIONEER PROJECT 等几何字需要更多屏幕像素才不糊
    const targetWidth = Math.min(viewW * 0.3, viewH * 0.56)
    pivot.scale.setScalar(targetWidth / size.x)
    stage.scale.copy(pivot.scale)
    const pxW = (targetWidth / viewW) * w
    const pxH = pxW * (size.y / size.x)
    hud.value = { x: ANCHOR.x * w, y: ANCHOR.y * h, w: pxW, h: pxH }
  }

  const pointer = new T.Vector2()
  const smoothPointer = new T.Vector2()
  let lastStillRender = 0
  function onPointerMove(e: PointerEvent) {
    pointer.set((e.clientX / window.innerWidth) * 2 - 1, (e.clientY / window.innerHeight) * 2 - 1)
    if (reduceMotion) {
      const now = performance.now()
      // 低动效路径也限到 ~30fps，避免 pointermove 风暴
      if (now - lastStillRender < FRAME_MS) return
      lastStillRender = now
      smoothPointer.copy(pointer)
      renderStill()
    }
  }

  const timer = new T.Timer()
  function pose(t: number) {
    if (!reduceMotion) smoothPointer.lerp(pointer, 0.09)
    const unit = pivot.scale.x * size.y
    const bobAmp = lite ? 0.02 : 0.035
    const bob = reduceMotion ? 0 : Math.sin(t * 0.9) * unit * bobAmp
    pivot.position.set(base.x, base.y + bob, base.z)
    stage.position.set(base.x, base.y + bob * 0.35, base.z)
    animateStage(t)
    // 基准角更正对镜头，几何字/磁带少吃 MSAA 斜边抹软
    pivot.rotation.set(
      0.12 + (reduceMotion ? 0 : Math.sin(t * 0.6) * 0.025) + smoothPointer.y * 0.14,
      0.28 + (reduceMotion ? 0 : Math.sin(t * 0.35) * 0.06) + smoothPointer.x * 0.2,
      reduceMotion ? 0 : Math.sin(t * 0.5) * 0.02,
    )
  }

  let frame = 0
  let lastFrameTime = 0
  function tick(timestamp: number) {
    frame = requestAnimationFrame(tick)
    if (timestamp - lastFrameTime < FRAME_MS) return
    lastFrameTime = timestamp
    timer.update(timestamp)
    pose(timer.getElapsed())
    renderer.render(scene, camera)
  }
  function renderStill() {
    pose(0)
    renderer.render(scene, camera)
  }
  function start() {
    if (reduceMotion || frame || document.hidden) return
    timer.reset()
    lastFrameTime = 0
    frame = requestAnimationFrame(tick)
  }
  function stop() {
    cancelAnimationFrame(frame)
    frame = 0
  }
  function onVisibility() {
    if (document.hidden) stop()
    else start()
  }

  const resizeObserver = new ResizeObserver(() => {
    layout()
    if (reduceMotion) renderStill()
  })
  resizeObserver.observe(el)
  layout()
  renderStill()
  ready.value = true
  window.addEventListener('pointermove', onPointerMove, { passive: true })
  document.addEventListener('visibilitychange', onVisibility)
  start()

  teardown = () => {
    stop()
    resizeObserver.disconnect()
    window.removeEventListener('pointermove', onPointerMove)
    document.removeEventListener('visibilitychange', onVisibility)
    timer.dispose()
    disposeScene()
    renderer.dispose()
    renderer.domElement.remove()
  }
}

onMounted(() => {
  if (host.value) setup(host.value).catch(() => {})
})

onBeforeUnmount(() => {
  unmounted = true
  teardown?.()
})
</script>

<template>
  <div ref="host" class="login-scene" :class="{ 'login-scene-ready': ready }" aria-hidden="true">
    <div
      v-if="hud.w"
      class="scene-hud"
      :style="{ left: `${hud.x}px`, top: `${hud.y}px`, width: `${hud.w * 1.5}px`, height: `${hud.h * 2.3}px` }"
    >
      <i class="hud-corner hud-tl"></i><i class="hud-corner hud-tr"></i><i class="hud-corner hud-bl"></i><i class="hud-corner hud-br"></i>
      <span class="hud-tag hud-tag-top">UNIT·07 <b>DATA MODULE</b></span>
      <span class="hud-tag hud-tag-side">Ø 0.62 · Z+04</span>
      <span class="hud-tag hud-tag-bottom"><i class="hud-blink"></i>SIGNAL LOCKED</span>
    </div>
  </div>
</template>

<style scoped>
.login-scene {
  position: absolute;
  inset: 0;
  opacity: 0;
  transition: opacity 0.8s ease;
}
.login-scene-ready {
  opacity: 1;
}
.login-scene :deep(canvas) {
  display: block;
  width: 100%;
  height: 100%;
}

/* HUD：卡带未来主义的琥珀色细线框，跟随模块；画布就绪后才淡入 */
.scene-hud {
  --hud-ink: rgb(243 150 92 / 0.72);
  position: absolute;
  transform: translate(-50%, -42%);
  pointer-events: none;
  opacity: 0;
  transition: opacity 1.2s ease 0.5s;
}
.login-scene-ready .scene-hud {
  opacity: 1;
}
.hud-corner {
  position: absolute;
  width: 18px;
  height: 18px;
  border: 0 solid var(--hud-ink);
}
.hud-tl {
  top: 0;
  left: 0;
  border-top-width: 1px;
  border-left-width: 1px;
}
.hud-tr {
  top: 0;
  right: 0;
  border-top-width: 1px;
  border-right-width: 1px;
}
.hud-bl {
  bottom: 0;
  left: 0;
  border-bottom-width: 1px;
  border-left-width: 1px;
}
.hud-br {
  right: 0;
  bottom: 0;
  border-right-width: 1px;
  border-bottom-width: 1px;
}
.hud-tag {
  position: absolute;
  display: inline-flex;
  align-items: center;
  gap: 0.5em;
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.18em;
  white-space: nowrap;
  color: rgb(245 237 220 / 0.6);
}
.hud-tag b {
  font-weight: 500;
  color: var(--hud-ink);
}
.hud-tag-top {
  top: -1.6em;
  left: 0;
}
.hud-tag-side {
  top: 50%;
  right: -1.2em;
  transform: translate(100%, -50%) rotate(90deg);
  transform-origin: left center;
  color: rgb(245 237 220 / 0.38);
}
.hud-tag-bottom {
  right: 0;
  bottom: -1.7em;
  color: var(--hud-ink);
}
.hud-blink {
  width: 5px;
  height: 5px;
  border-radius: 50%;
  background: #f36b18;
  box-shadow: 0 0 6px #f36b18;
  animation: hud-blink 1.6s steps(1) infinite;
}
@keyframes hud-blink {
  50% {
    opacity: 0.15;
  }
}
@media (prefers-reduced-motion: reduce) {
  .hud-blink {
    animation: none;
  }
}
</style>
