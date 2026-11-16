<script setup lang="ts">
/**
 * 登录页 3D 背景：走廊背景图 + 悬浮的数据卡带模块。
 * three 及其扩展按需动态加载，打成单独分块；加载完成并画出第一帧后画布才淡入，
 * 在此之前由外层的 CSS 背景图顶替。
 *
 * 性能策略：无后处理、原生 MSAA、DPR≤2（弱设备≤1.5）、约 30fps、3 盏本地光。
 * 观察窗关掉 transmission（改半透明），避免透射 RT 把正面字/磁带抹糊。
 */
import { onBeforeUnmount, onMounted, ref } from 'vue'
import type * as THREE from 'three'
import bgUrl from '@/assets/login/login-bg.webp'
import modelUrl from '@/assets/login/data-module.glb?url'

const host = ref<HTMLDivElement>()
const ready = ref(false)

let teardown: (() => void) | null = null
let unmounted = false

/** 模型中心在视口中的位置（0–1），落在左侧主视觉区偏右的上半部分 */
const ANCHOR = { x: 0.36, y: 0.4 }
const CAMERA_DISTANCE = 6
/** 装饰场景无需 60fps；30fps 足够，显著降低 GPU/电池占用 */
const FRAME_MS = 1000 / 30

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
      color: 0x050608,
      roughness: 1,
      metalness: 0,
      side: T.BackSide,
    }),
  )
  cavity.scale.set(12, 6, 18)
  env.add(cavity)

  const wallMat = new T.MeshStandardMaterial({
    color: 0x15181e,
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

/** 极淡软边圆形接触阴影纹理（64² 足够，阴影本身很糊） */
function createContactShadowTexture(T: typeof THREE): THREE.CanvasTexture {
  const size = 64
  const canvas = document.createElement('canvas')
  canvas.width = size
  canvas.height = size
  const ctx = canvas.getContext('2d')!
  const g = ctx.createRadialGradient(size / 2, size / 2, size * 0.08, size / 2, size / 2, size * 0.48)
  g.addColorStop(0, 'rgba(0,0,0,0.45)')
  g.addColorStop(0.45, 'rgba(0,0,0,0.18)')
  g.addColorStop(1, 'rgba(0,0,0,0)')
  ctx.fillStyle = g
  ctx.fillRect(0, 0, size, size)
  const tex = new T.CanvasTexture(canvas)
  tex.colorSpace = T.SRGBColorSpace
  return tex
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
  renderer.toneMappingExposure = 0.98
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
  scene.environmentIntensity = lite ? 1.25 : 1.85

  const key = new T.DirectionalLight(0xfff3e8, 1.55)
  key.position.set(-1.5, 5, 4)
  const rim = new T.DirectionalLight(0xa8d8ff, 1.2)
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
            std.roughness = Math.max(0.04, (std.roughness ?? 0.4) * 0.45)
          } else if (typeof std.roughness === 'number') {
            std.roughness = Math.max(0.12, std.roughness * 0.9)
          }
        }
        std.fog = false
      }
      // 透射亚克力观察窗：transmission 走低分 RT，会把窗后几何字/磁带抹成一片
      const phys = m as THREE.MeshPhysicalMaterial
      if (phys.isMeshPhysicalMaterial && phys.transmission > 0) {
        phys.transmission = 0
        phys.transparent = true
        phys.opacity = 0.12
        phys.depthWrite = false
        phys.roughness = 0.03
        phys.metalness = 0
        phys.envMapIntensity = lite ? 1.5 : 2.0
        phys.side = T.FrontSide
        if ('clearcoat' in phys) {
          phys.clearcoat = 0.85
          phys.clearcoatRoughness = 0.04
        }
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
    bgTexture.dispose()
    envTexture.dispose()
  }
  if (unmounted) {
    disposeScene()
    renderer.dispose()
    return
  }
  el.appendChild(renderer.domElement)
  bgTexture.colorSpace = T.SRGBColorSpace
  // 背景图分辨率往往高于视口；限制各向异性与 mip 生成外的过滤即可
  bgTexture.anisotropy = 1
  bgTexture.generateMipmaps = true
  bgTexture.minFilter = T.LinearMipmapLinearFilter
  bgTexture.magFilter = T.LinearFilter
  scene.background = bgTexture

  const pivot = new T.Group()
  const box = new T.Box3().setFromObject(model)
  const size = box.getSize(new T.Vector3())
  model.position.sub(box.getCenter(new T.Vector3()))
  pivot.add(model)

  const shadowTex = createContactShadowTexture(T)
  const shadow = new T.Mesh(
    new T.PlaneGeometry(1, 1),
    new T.MeshBasicMaterial({
      map: shadowTex,
      transparent: true,
      opacity: 0.55,
      depthWrite: false,
      fog: false,
    }),
  )
  shadow.rotation.x = -Math.PI / 2
  shadow.position.set(0, -size.y * 0.52, 0)
  shadow.scale.set(size.x * 1.35, size.z * 1.1, 1)
  shadow.renderOrder = -1
  pivot.add(shadow)

  // 跟随模块的局部高光：正面包边一抹暖白，侧棱一点冷闪
  const faceSpec = new T.SpotLight(0xfff6ea, lite ? 12 : 20, size.x * 6, Math.PI / 6, 0.62, 1.6)
  faceSpec.position.set(-size.x * 0.55, size.y * 0.75, size.z * 1.55)
  faceSpec.target.position.set(0, size.y * 0.05, size.z * 0.35)
  const edgeSpec = new T.SpotLight(0xeaf2ff, lite ? 7 : 12, size.x * 5, Math.PI / 7, 0.7, 1.8)
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

    const img = bgTexture.image as { width: number; height: number }
    const imageAspect = img.width / img.height
    const viewAspect = w / h
    if (viewAspect > imageAspect) bgTexture.repeat.set(1, imageAspect / viewAspect)
    else bgTexture.repeat.set(viewAspect / imageAspect, 1)
    bgTexture.offset.set((1 - bgTexture.repeat.x) / 2, (1 - bgTexture.repeat.y) / 2)

    const viewH = 2 * CAMERA_DISTANCE * Math.tan(T.MathUtils.degToRad(camera.fov / 2))
    const viewW = viewH * camera.aspect
    base.set((ANCHOR.x - 0.5) * viewW, (0.5 - ANCHOR.y) * viewH, 0)
    // 略放大：PIONEER PROJECT 等几何字需要更多屏幕像素才不糊
    const targetWidth = Math.min(viewW * 0.3, viewH * 0.56)
    pivot.scale.setScalar(targetWidth / size.x)
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
  <div ref="host" class="login-scene" :class="{ 'login-scene-ready': ready }" aria-hidden="true"></div>
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
</style>
