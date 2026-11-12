<script setup lang="ts">
/**
 * 深空背景：向后掠过的三层星点、四芒星、赤纬弧与一道周期划过的星迹。
 * 位置由固定种子生成，保证每次渲染一致。
 */
function seeded(seed: number) {
  let s = seed
  return () => {
    s = (s * 1664525 + 1013904223) % 4294967296
    return s / 4294967296
  }
}
const rand = seeded(20261112)

// 三层景深：远层小而慢，近层大而快——飞船向前（画面上方）航行时的视差
const layer = (count: number, rMin: number, rMax: number, oMin: number, oMax: number) =>
  Array.from({ length: count }, () => ({
    x: +(rand() * 1000).toFixed(1),
    y: +(rand() * 800).toFixed(1),
    r: +(rMin + rand() * (rMax - rMin)).toFixed(2),
    o: +(oMin + rand() * (oMax - oMin)).toFixed(2),
    twinkle: rand() < 0.3,
    delay: +(rand() * 6).toFixed(2),
    dur: +(3.5 + rand() * 4).toFixed(2),
  }))
const layers = [
  { name: 'far', dots: layer(60, 0.45, 0.85, 0.16, 0.42) },
  { name: 'mid', dots: layer(28, 0.8, 1.2, 0.3, 0.6) },
  { name: 'near', dots: layer(12, 1, 1.5, 0.45, 0.75) },
]

const star = (s: number) => `M0 ${-s}Q0 0 ${s} 0Q0 0 0 ${s}Q0 0 ${-s} 0Q0 0 0 ${-s}Z`
const sparkles = [
  { x: 118, y: 196, s: 6 },
  { x: 628, y: 58, s: 5 },
  { x: 548, y: 706, s: 4.5 },
].map((p, i) => ({ ...p, d: star(p.s), delay: i * 2.4 }))
</script>

<template>
  <svg class="space" viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid slice" fill="none" aria-hidden="true">
    <defs>
      <linearGradient id="space-trail" gradientUnits="userSpaceOnUse" x1="60" y1="372" x2="604" y2="150">
        <stop offset="0" stop-color="#F36B18" stop-opacity="0" />
        <stop offset="0.55" stop-color="#F36B18" stop-opacity="0.55" />
        <stop offset="1" stop-color="#F36B18" />
      </linearGradient>
      <radialGradient id="space-haze" cx="0.78" cy="0.5" r="0.6">
        <stop offset="0" stop-color="#F36B18" stop-opacity="0.1" />
        <stop offset="0.55" stop-color="#958A78" stop-opacity="0.05" />
        <stop offset="1" stop-color="#958A78" stop-opacity="0" />
      </radialGradient>
    </defs>

    <rect width="1000" height="800" fill="url(#space-haze)" />

    <!-- 赤纬弧：大半径同心弧，暗示天球坐标 -->
    <g stroke="#F5EDDC" stroke-opacity="0.07">
      <circle cx="1040" cy="1180" r="760" />
      <circle cx="1040" cy="1180" r="920" stroke-dasharray="2 10" />
      <circle cx="1040" cy="1180" r="1080" />
      <circle cx="1040" cy="1180" r="1240" stroke-dasharray="2 10" />
    </g>

    <!-- 星点：分三层以不同速度向下掠过；每层上方叠一份相同的星点，循环时无缝衔接 -->
    <g v-for="l in layers" :key="l.name" class="drift" :class="'drift-' + l.name">
      <g v-for="offset in [0, -800]" :key="offset" :transform="`translate(0 ${offset})`">
        <circle
          v-for="(d, i) in l.dots"
          :key="i"
          :cx="d.x"
          :cy="d.y"
          :r="d.r"
          fill="#F5EDDC"
          :fill-opacity="d.o"
          :class="{ twinkle: l.name === 'far' && d.twinkle }"
          :style="
            l.name === 'far' && d.twinkle
              ? { animationDelay: d.delay + 's', animationDuration: d.dur + 's' }
              : undefined
          "
        />
      </g>
    </g>

    <!-- 四芒星 -->
    <path
      v-for="(s, i) in sparkles"
      :key="'s' + i"
      class="sparkle"
      :d="s.d"
      :transform="`translate(${s.x} ${s.y})`"
      fill="#F5EDDC"
      :style="{ animationDelay: s.delay + 's' }"
    />

    <!-- 周期划过的橙色星迹 -->
    <g class="streak">
      <path class="streak-trail" d="M60 372C190 250 400 168 604 150" stroke="url(#space-trail)" stroke-width="3.5" pathLength="1" />
      <path class="streak-head" :d="star(10)" transform="translate(604 150)" fill="#F36B18" />
    </g>
  </svg>
</template>

<style scoped>
.space {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.drift-far {
  animation: space-drift 150s linear infinite;
}
.drift-mid {
  animation: space-drift 70s linear infinite;
}
.drift-near {
  animation: space-drift 26s linear infinite;
}
.twinkle {
  animation: space-twinkle 5s ease-in-out infinite;
}
.sparkle {
  opacity: 0.35;
  animation: space-sparkle 8s ease-in-out infinite;
}
.streak-trail {
  stroke-dasharray: 1;
  animation: space-streak 13s cubic-bezier(0.3, 0.6, 0.2, 1) infinite;
}
.streak-head {
  animation: space-streak-head 13s ease-out infinite;
}

@keyframes space-drift {
  to {
    transform: translateY(800px);
  }
}
@keyframes space-twinkle {
  0%,
  100% {
    opacity: 1;
  }
  50% {
    opacity: 0.2;
  }
}
@keyframes space-sparkle {
  0%,
  100% {
    opacity: 0.1;
  }
  50% {
    opacity: 0.55;
  }
}
@keyframes space-streak {
  0% {
    stroke-dashoffset: 1;
    opacity: 0;
  }
  3% {
    opacity: 1;
  }
  16% {
    stroke-dashoffset: 0;
    opacity: 1;
  }
  46% {
    stroke-dashoffset: 0;
    opacity: 0.85;
  }
  60%,
  100% {
    stroke-dashoffset: 0;
    opacity: 0;
  }
}
@keyframes space-streak-head {
  0%,
  13% {
    opacity: 0;
  }
  17% {
    opacity: 1;
  }
  46% {
    opacity: 0.9;
  }
  60%,
  100% {
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .drift,
  .twinkle,
  .sparkle,
  .streak-trail,
  .streak-head {
    animation: none;
  }
}
</style>
