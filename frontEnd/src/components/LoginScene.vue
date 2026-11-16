<script setup lang="ts">
/**
 * 登录页 3D 背景：走廊背景图 + 悬浮的数据卡带模块。
 * three 及其扩展按需动态加载，打成单独分块；加载完成并画出第一帧后画布才淡入，
 * 在此之前由外层的 CSS 背景图顶替。
 *
 * 性能策略：无后处理、原生 MSAA、DPR≤1.25（弱设备≤1）、约 30fps、3 盏本地光。
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
 * 深色腔体 + 顶/侧冷白 emissive 条带 + 底部弱红，替代摄影棚 RoomEnvironment。
 */
function createCorridorEnvironment(T: typeof THREE): THREE.Scene {
  const env = new T.Scene()
  env.name = 'CorridorLightEnvironment'

  const boxGeo = new T.BoxGeometry(1, 1, 1)
  boxGeo.deleteAttribute('uv')

  const cavity = new T.Mesh(
    boxGeo,
    new T.MeshStandardMaterial({
      color: 0x1a1d22,
      roughness: 0.92,
      metalness: 0.08,
      side: T.BackSide,
    }),
  )
  cavity.scale.set(12, 6, 18)
  env.add(cavity)

  const wallMat = new T.MeshStandardMaterial({
    color: 0x2a3038,
    roughness: 0.78,
    metalness: 0.35,
  })
  const leftWall = new T.Mesh(boxGeo, wallMat)
  leftWall.position.set(-4.2, 0, 0)
  leftWall.scale.set(0.35, 5.2, 16)
  const rightWall = new T.Mesh(boxGeo, wallMat)
  rightWall.position.set(4.2, 0, 0)
  rightWall.scale.set(0.35, 5.2, 16)
  env.add(leftWall, rightWall)

  const stripMat = new T.MeshStandardMaterial({
    color: 0xffffff,
    emissive: 0xe8f2ff,
    emissiveIntensity: 8,
    roughness: 1,
    metalness: 0,
  })
  function addStrip(x: number, y: number, z: number, sx: number, sy: number, sz: number) {
    const strip = new T.Mesh(boxGeo, stripMat)
    strip.position.set(x, y, z)
    strip.scale.set(sx, sy, sz)
    env.add(strip)
  }
  addStrip(0, 2.85, 0, 0.35, 0.08, 14)
  addStrip(-1.6, 2.85, 0, 0.18, 0.06, 12)
  addStrip(1.6, 2.85, 0, 0.18, 0.06, 12)
  addStrip(-3.9, 1.2, 0, 0.06, 0.12, 10)
  addStrip(3.9, 1.2, 0, 0.06, 0.12, 10)

  const floorGlow = new T.Mesh(
    boxGeo,
    new T.MeshStandardMaterial({
      color: 0x1a0808,
      emissive: 0xff2a1f,
      emissiveIntensity: 1.4,
      roughness: 1,
      metalness: 0,
    }),
  )
  floorGlow.position.set(0, -2.7, 2)
  floorGlow.scale.set(3.5, 0.05, 4)
  env.add(floorGlow)

  const fill = new T.PointLight(0xeef4ff, 40, 20, 2)
  fill.position.set(0, 2.4, 2)
  const sideFill = new T.PointLight(0xb8d4ff, 18, 14, 2)
  sideFill.position.set(-3.2, 1.4, -1)
  const redFill = new T.PointLight(0xff3b2f, 12, 10, 2)
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
      powerPreference: 'low-power',
      stencil: false,
      depth: true,
    })
  } catch {
    return
  }
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const lite = isLiteDevice()
  // 弱设备 DPR≤1；其余允许到 1.25，配合 MSAA 压金属边缘锯齿
  const pixelRatio = Math.min(window.devicePixelRatio || 1, lite ? 1 : 1.25)
  renderer.setPixelRatio(pixelRatio)
  renderer.toneMapping = T.NeutralToneMapping
  renderer.toneMappingExposure = 0.98

  const scene = new T.Scene()
  const camera = new T.PerspectiveCamera(28, 1, 0.1, 100)
  camera.position.set(0, 0, CAMERA_DISTANCE)

  const corridorEnv = createCorridorEnvironment(T)
  const pmrem = new T.PMREMGenerator(renderer)
  // 弱设备略降 PMREM 采样模糊半径以外的成本主要在分辨率；fromScene 默认即可
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
  scene.environmentIntensity = lite ? 0.75 : 0.95

  // 3 盏本地光：顶光（含原灯带贡献）、轮廓、地面红；少一盏 PointLight 降低 PBR 片段开销
  const key = new T.DirectionalLight(0xeef3ff, 2.6)
  key.position.set(-1.5, 5, 4)
  const rim = new T.DirectionalLight(0xa8d8ff, 1.8)
  rim.position.set(3.5, 1.5, -4)
  const glow = new T.PointLight(0xff3b2f, 8, 9, 2)
  glow.position.set(2.2, -2, 2.4)
  scene.add(key, rim, glow)

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
    const mats = ([] as THREE.Material[]).concat(mesh.material)
    for (const m of mats) {
      const std = m as THREE.MeshStandardMaterial
      if (std.isMeshStandardMaterial) {
        std.envMapIntensity = 1
        // 登录场景无阴影/无雾，关掉可能触发的额外通道
        std.fog = false
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
    const targetWidth = Math.min(viewW * 0.24, viewH * 0.46)
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
    pivot.rotation.set(
      0.22 + (reduceMotion ? 0 : Math.sin(t * 0.6) * 0.025) + smoothPointer.y * 0.16,
      0.5 + (reduceMotion ? 0 : Math.sin(t * 0.35) * 0.08) + smoothPointer.x * 0.22,
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
