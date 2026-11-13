<script setup lang="ts">
/**
 * 登录页 3D 背景：走廊背景图 + 悬浮的数据卡带模块。
 * three 及其扩展按需动态加载，打成单独分块；加载完成并画出第一帧后画布才淡入，
 * 在此之前由外层的 CSS 背景图顶替。
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

async function setup(el: HTMLDivElement) {
  const [T, { GLTFLoader }, { MeshoptDecoder }, { RoomEnvironment }, { EffectComposer }, { RenderPass }, { BokehPass }, { OutputPass }] =
    await Promise.all([
      import('three'),
      import('three/addons/loaders/GLTFLoader.js'),
      import('three/addons/libs/meshopt_decoder.module.js'),
      import('three/addons/environments/RoomEnvironment.js'),
      import('three/addons/postprocessing/EffectComposer.js'),
      import('three/addons/postprocessing/RenderPass.js'),
      import('three/addons/postprocessing/BokehPass.js'),
      import('three/addons/postprocessing/OutputPass.js'),
    ])
  if (unmounted) return

  let renderer: THREE.WebGLRenderer
  try {
    renderer = new T.WebGLRenderer({ antialias: false, powerPreference: 'high-performance' })
  } catch {
    return
  }
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 1.5)
  renderer.setPixelRatio(pixelRatio)
  // 后处理的 OutputPass 会对整帧（含背景图）做色调映射；Neutral 只压高光，背景图基本保持原色
  renderer.toneMapping = T.NeutralToneMapping
  renderer.toneMappingExposure = 1

  const scene = new T.Scene()
  const camera = new T.PerspectiveCamera(28, 1, 0.1, 100)
  camera.position.set(0, 0, CAMERA_DISTANCE)

  const pmrem = new T.PMREMGenerator(renderer)
  const envTexture = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  pmrem.dispose()
  scene.environment = envTexture
  scene.environmentIntensity = 0.55

  // 冷白主光对应走廊顶部灯带；背后冷色轮廓光勾边；右下方弱红光呼应走廊地面的红色
  const key = new T.DirectionalLight(0xeef3ff, 2.4)
  key.position.set(-3, 4, 5)
  const rim = new T.DirectionalLight(0xa8d8ff, 3.2)
  rim.position.set(4, 2.5, -4)
  const glow = new T.PointLight(0xff3b2f, 14, 9, 2)
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
  scene.add(model)

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
  scene.background = bgTexture

  const pivot = new T.Group()
  const box = new T.Box3().setFromObject(model)
  const size = box.getSize(new T.Vector3())
  model.position.sub(box.getCenter(new T.Vector3()))
  pivot.add(model)
  scene.add(pivot)

  const target = new T.WebGLRenderTarget(1, 1, { type: T.HalfFloatType, samples: 4 })
  const composer = new EffectComposer(renderer, target)
  composer.setPixelRatio(pixelRatio)
  composer.addPass(new RenderPass(scene, camera))
  const bokeh = new BokehPass(scene, camera, { focus: CAMERA_DISTANCE, aperture: 0.004, maxblur: 0.005 })
  composer.addPass(bokeh)
  composer.addPass(new OutputPass())

  const base = new T.Vector3()
  function layout() {
    const w = el.clientWidth
    const h = el.clientHeight
    if (!w || !h) return
    renderer.setSize(w, h, false)
    composer.setSize(w, h)
    camera.aspect = w / h
    camera.updateProjectionMatrix()

    // 背景图按 cover 方式铺满
    const img = bgTexture.image as { width: number; height: number }
    const imageAspect = img.width / img.height
    const viewAspect = w / h
    if (viewAspect > imageAspect) bgTexture.repeat.set(1, imageAspect / viewAspect)
    else bgTexture.repeat.set(viewAspect / imageAspect, 1)
    bgTexture.offset.set((1 - bgTexture.repeat.x) / 2, (1 - bgTexture.repeat.y) / 2)

    // 模型放到锚点位置：按相机距离处的可视范围换算成世界坐标，宽度取视口宽高的较小约束
    const viewH = 2 * CAMERA_DISTANCE * Math.tan(T.MathUtils.degToRad(camera.fov / 2))
    const viewW = viewH * camera.aspect
    base.set((ANCHOR.x - 0.5) * viewW, (0.5 - ANCHOR.y) * viewH, 0)
    const targetWidth = Math.min(viewW * 0.24, viewH * 0.46)
    pivot.scale.setScalar(targetWidth / size.x)
  }

  const pointer = new T.Vector2()
  const smoothPointer = new T.Vector2()
  function onPointerMove(e: PointerEvent) {
    pointer.set((e.clientX / window.innerWidth) * 2 - 1, (e.clientY / window.innerHeight) * 2 - 1)
  }

  const timer = new T.Timer()
  function pose(t: number) {
    smoothPointer.lerp(pointer, 0.04)
    const unit = pivot.scale.x * size.y
    pivot.position.set(base.x, base.y + Math.sin(t * 0.9) * unit * 0.06, base.z)
    pivot.rotation.set(
      0.22 + Math.sin(t * 0.6) * 0.05 + smoothPointer.y * 0.08,
      -0.5 + Math.sin(t * 0.35) * 0.3 + smoothPointer.x * 0.12,
      Math.sin(t * 0.5) * 0.04,
    )
  }

  let frame = 0
  function tick(timestamp: number) {
    frame = requestAnimationFrame(tick)
    timer.update(timestamp)
    pose(timer.getElapsed())
    composer.render()
  }
  function renderStill() {
    pose(0)
    composer.render()
  }
  function start() {
    if (reduceMotion || frame || document.hidden) return
    // 从暂停处继续计时，避免切回标签页时姿态跳变
    timer.reset()
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
    bokeh.dispose()
    composer.dispose()
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
