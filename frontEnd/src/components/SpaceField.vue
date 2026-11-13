<script setup lang="ts">
/**
 * 深空背景：向后掠过的三层星点、四芒星、赤纬弧与一道周期划过的星迹。
 * 位置由固定种子生成，保证每次渲染一致。
 *
 * 会动的部分都是独立图层，只做变换或透明度动画：每层星点画一次，整层平移；
 * 闪烁、四芒星与星迹各自只改透明度。静态部分（光晕、赤纬弧）是一张不动的 SVG。
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
    x: +(rand() * 100).toFixed(2),
    y: +(rand() * 100).toFixed(2),
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
/** 每层上下叠两份相同的星点（各占一半高度），整层平移一份的高度即可无缝循环 */
const copies = [0, 50]

const star = (s: number) => `M0 ${-s}Q0 0 ${s} 0Q0 0 0 ${s}Q0 0 ${-s} 0Q0 0 0 ${-s}Z`
const sparkles = [
  { x: 11.8, y: 24.5, s: 6 },
  { x: 62.8, y: 7.25, s: 5 },
  { x: 54.8, y: 88.25, s: 4.5 },
].map((p, i) => ({ ...p, d: star(p.s), delay: i * 2.4 }))
</script>

<template>
  <div class="space" aria-hidden="true">
    <svg class="space-static" viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid slice" fill="none">
      <defs>
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
    </svg>

    <!-- 星点：分三层以不同速度向下掠过 -->
    <div v-for="l in layers" :key="l.name" class="drift" :class="'drift-' + l.name">
      <template v-for="offset in copies" :key="offset">
        <i
          v-for="(d, i) in l.dots"
          :key="i"
          class="dot"
          :class="{ twinkle: l.name === 'far' && d.twinkle }"
          :style="{
            left: d.x + '%',
            top: offset + d.y / 2 + '%',
            '--size': d.r * 2.4 + 'px',
            '--o': d.o,
            ...(l.name === 'far' && d.twinkle ? { animationDelay: d.delay + 's', animationDuration: d.dur + 's' } : {}),
          }"
        ></i>
      </template>
    </div>

    <!-- 四芒星 -->
    <svg
      v-for="(s, i) in sparkles"
      :key="'s' + i"
      class="sparkle"
      :viewBox="`${-s.s} ${-s.s} ${s.s * 2} ${s.s * 2}`"
      :style="{ left: s.x + '%', top: s.y + '%', '--size': s.s * 2.4 + 'px', animationDelay: s.delay + 's' }"
    >
      <path :d="s.d" fill="#F5EDDC" />
    </svg>

    <!-- 周期划过的橙色星迹 -->
    <svg class="streak streak-trail" viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid slice" fill="none">
      <defs>
        <linearGradient id="space-trail" gradientUnits="userSpaceOnUse" x1="60" y1="372" x2="604" y2="150">
          <stop offset="0" stop-color="#F36B18" stop-opacity="0" />
          <stop offset="0.55" stop-color="#F36B18" stop-opacity="0.55" />
          <stop offset="1" stop-color="#F36B18" />
        </linearGradient>
      </defs>
      <path d="M60 372C190 250 400 168 604 150" stroke="url(#space-trail)" stroke-width="3.5" pathLength="1" />
    </svg>
    <svg class="streak streak-head" viewBox="0 0 1000 800" preserveAspectRatio="xMidYMid slice" fill="none">
      <path :d="star(10)" transform="translate(604 150)" fill="#F36B18" />
    </svg>
  </div>
</template>

<style scoped>
.space,
.space-static,
.streak {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
.space {
  overflow: hidden;
  pointer-events: none;
}
/* 两份星点上下相接，整层高 200%；向下平移一半（一份的高度）后与起点重合 */
.drift {
  position: absolute;
  left: 0;
  right: 0;
  top: -100%;
  height: 200%;
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
.dot {
  position: absolute;
  width: var(--size);
  height: var(--size);
  border-radius: 50%;
  /* 亮度放在颜色里，闪烁动画用固定的透明度区间，才能交给合成线程 */
  background: rgb(245 237 220 / var(--o));
  translate: -50% -50%;
}
.twinkle {
  animation: space-twinkle 5s ease-in-out infinite;
}
.sparkle {
  position: absolute;
  width: var(--size);
  height: var(--size);
  translate: -50% -50%;
  opacity: 0.35;
  animation: space-sparkle 8s ease-in-out infinite;
}
.streak-trail path {
  stroke-dasharray: 1;
  animation: space-streak-draw 13s cubic-bezier(0.3, 0.6, 0.2, 1) infinite;
}
.streak-trail {
  animation: space-streak 13s cubic-bezier(0.3, 0.6, 0.2, 1) infinite;
}
.streak-head {
  animation: space-streak-head 13s ease-out infinite;
}

@keyframes space-drift {
  to {
    transform: translateY(50%);
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
/* 描线只在每轮开头的一小段时间里变化，其余时间保持画满 */
@keyframes space-streak-draw {
  0% {
    stroke-dashoffset: 1;
  }
  16%,
  100% {
    stroke-dashoffset: 0;
  }
}
@keyframes space-streak {
  0% {
    opacity: 0;
  }
  3%,
  16% {
    opacity: 1;
  }
  46% {
    opacity: 0.85;
  }
  60%,
  100% {
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
  .streak-trail path,
  .streak-head {
    animation: none;
  }
}
</style>
