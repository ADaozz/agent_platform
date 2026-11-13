<script setup lang="ts">
/**
 * 磁带蒙版：铺满所在的背景层，模拟录像带与胶片的瑕疵——
 * 暖色光渗、颗粒噪点、扫描线、暗角、偶发的走带干扰条与划痕。
 * 只动 transform / opacity，不用混合模式（混合需要每帧读取下层像素重新合成）；不拦截指针事件。
 */
const grain =
  "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/%3E%3CfeColorMatrix values='0 0 0 0 0.96 0 0 0 0 0.93 0 0 0 0 0.86 0 0 0 0.55 0'/%3E%3C/filter%3E%3Crect width='180' height='180' filter='url(%23n)'/%3E%3C/svg%3E\")"
</script>

<template>
  <div class="tape" aria-hidden="true">
    <div class="tape-bleed tape-bleed-a"></div>
    <div class="tape-bleed tape-bleed-b"></div>
    <div class="tape-grain" :style="{ backgroundImage: grain }"></div>
    <div class="tape-scan"></div>
    <div class="tape-scratch tape-scratch-a"></div>
    <div class="tape-scratch tape-scratch-b"></div>
    <div class="tape-track"></div>
    <div class="tape-vignette"></div>
  </div>
</template>

<style scoped>
.tape {
  position: absolute;
  inset: 0;
  z-index: 2;
  overflow: hidden;
  pointer-events: none;
}
.tape > div {
  position: absolute;
}

/* 光渗：亮部周围的暖色晕染，缓慢呼吸 */
.tape-bleed {
  border-radius: 50%;
  animation: tape-breathe 9s ease-in-out infinite;
}
.tape-bleed-a {
  top: 8%;
  right: -22%;
  width: 85%;
  aspect-ratio: 1;
  background: radial-gradient(circle, rgb(226 133 79 / 0.16), rgb(223 169 60 / 0.05) 45%, transparent 70%);
}
.tape-bleed-b {
  bottom: -30%;
  left: -20%;
  width: 70%;
  aspect-ratio: 1;
  background: radial-gradient(circle, rgb(200 73 64 / 0.1), transparent 65%);
  animation-delay: -4.5s;
}

/* 颗粒噪点：比画面大一圈，按帧跳动位置 */
.tape-grain {
  inset: -60px;
  opacity: 0.06;
  background-size: 180px 180px;
  animation: tape-grain 0.9s steps(1) infinite;
}

/* 扫描线 */
.tape-scan {
  inset: 0;
  background: repeating-linear-gradient(0deg, rgb(0 0 0 / 0.2) 0 1px, transparent 1px 3px);
  opacity: 0.45;
}

/* 胶片划痕：两道细竖线，偶尔闪现 */
.tape-scratch {
  top: 0;
  bottom: 0;
  width: 1px;
  background: linear-gradient(transparent, rgb(245 237 220 / 0.16) 30%, rgb(245 237 220 / 0.05) 70%, transparent);
  opacity: 0;
  animation: tape-scratch 7s steps(1) infinite;
}
.tape-scratch-a {
  left: 31%;
}
.tape-scratch-b {
  left: 68%;
  animation-delay: -3.2s;
  animation-duration: 9.5s;
}

/* 走带干扰：一条偏亮的横带自上而下扫过，大部分时间不出现 */
.tape-track {
  top: 0;
  left: 0;
  right: 0;
  height: 70px;
  background: linear-gradient(
    transparent,
    rgb(245 237 220 / 0.035) 40%,
    rgb(245 237 220 / 0.09) 52%,
    rgb(245 237 220 / 0.02) 58%,
    transparent
  );
  opacity: 0;
  transform: translateY(-80px);
  animation: tape-track 11s linear infinite;
}

/* 暗角 */
.tape-vignette {
  inset: 0;
  background: radial-gradient(ellipse 80% 75% at 55% 50%, transparent 55%, rgb(0 0 0 / 0.5));
}

@keyframes tape-breathe {
  0%,
  100% {
    opacity: 0.7;
  }
  50% {
    opacity: 1;
  }
}
@keyframes tape-grain {
  0% {
    transform: translate(0, 0);
  }
  20% {
    transform: translate(-37px, 22px);
  }
  40% {
    transform: translate(18px, -41px);
  }
  60% {
    transform: translate(-12px, 33px);
  }
  80% {
    transform: translate(41px, 9px);
  }
}
@keyframes tape-scratch {
  0%,
  100% {
    opacity: 0;
  }
  62% {
    opacity: 1;
  }
  64% {
    opacity: 0.3;
  }
  66% {
    opacity: 0.9;
  }
  68% {
    opacity: 0;
  }
}
@keyframes tape-track {
  0%,
  44% {
    opacity: 0;
    transform: translateY(-80px);
  }
  45% {
    opacity: 1;
  }
  57% {
    opacity: 1;
    transform: translateY(100vh);
  }
  58%,
  100% {
    opacity: 0;
    transform: translateY(100vh);
  }
}
@media (prefers-reduced-motion: reduce) {
  .tape-bleed,
  .tape-grain,
  .tape-scratch,
  .tape-track {
    animation: none;
  }
}
</style>
