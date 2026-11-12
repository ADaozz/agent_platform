<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

/**
 * 陀螺仪星盘：纯 SVG。所有部件只在固定边界内往复（偏移 → 回正），不做整圈旋转。
 * 固定机架（刻度环 + 红黄绿读数弧）内是三层万向环：
 * 外环绕机架枢轴转、内环绕外环上的枢轴转、转子盘绕内环上的转子轴摆动并自旋。
 * 每层的姿态是真实的三维旋转 Rx(α)·Ry(β)·Rx(γ)，正投影后写成 SVG matrix；
 * 环的前半圈亮、后半圈暗，用来区分远近。减少动态效果时停在一个固定姿态。
 */
const point = (r: number, deg: number) => {
  const a = (deg * Math.PI) / 180;
  return `${(r * Math.sin(a)).toFixed(2)} ${(-r * Math.cos(a)).toFixed(2)}`;
};
/** 顺时针从正上方起算的圆弧 */
const arc = (r: number, from: number, to: number) =>
  `M${point(r, from)}A${r} ${r} 0 ${to - from > 180 ? 1 : 0} 1 ${point(r, to)}`;

/** 四芒星 */
const star = (s: number) =>
  `M0 ${-s}Q0 0 ${s} 0Q0 0 0 ${s}Q0 0 ${-s} 0Q0 0 0 ${-s}Z`;

const ROTOR_R = 100;

// 星迹：由短弧段拼成，越靠近星体越亮越粗
const TRAIL_SEGMENTS = 18;
const TRAIL_STEP = 5;
const trail = Array.from({ length: TRAIL_SEGMENTS }, (_, i) => {
  const t = (i + 1) / TRAIL_SEGMENTS;
  const from = -(TRAIL_SEGMENTS - i) * TRAIL_STEP;
  return {
    d: arc(ROTOR_R, from, from + TRAIL_STEP + 0.4),
    opacity: t * t * 0.95,
    width: 0.8 + t * 3.4,
  };
});

// 底部读数弧：绿 / 黄 / 红
const gauge = [
  { d: arc(190, 122, 157), color: "#83A695", delay: 0.6 },
  { d: arc(190, 162.5, 197.5), color: "#DFA93C", delay: 0.35 },
  { d: arc(190, 203, 238), color: "#C84940", delay: 0.1 },
];

type V3 = [number, number, number];
type M3 = [V3, V3, V3];
const rotX = (a: number): M3 => [
  [1, 0, 0],
  [0, Math.cos(a), -Math.sin(a)],
  [0, Math.sin(a), Math.cos(a)],
];
const rotY = (a: number): M3 => [
  [Math.cos(a), 0, Math.sin(a)],
  [0, 1, 0],
  [-Math.sin(a), 0, Math.cos(a)],
];
const mul = (a: M3, b: M3): M3 => {
  const row = (r: V3): V3 => [
    r[0] * b[0][0] + r[1] * b[1][0] + r[2] * b[2][0],
    r[0] * b[0][1] + r[1] * b[1][1] + r[2] * b[2][1],
    r[0] * b[0][2] + r[1] * b[1][2] + r[2] * b[2][2],
  ];
  return [row(a[0]), row(a[1]), row(a[2])];
};

const f = (n: number) => n.toFixed(4);
/** 环所在平面的正投影矩阵，以及让“前半圈”对准亮弧的面内转角 */
const pose = (m: M3) => ({
  matrix: `matrix(${f(m[0][0])} ${f(m[1][0])} ${f(m[0][1])} ${f(m[1][1])} 0 0)`,
  front: `rotate(${((Math.atan2(m[2][1], m[2][0]) * 180) / Math.PI).toFixed(2)})`,
});
/** 右半圆弧（配合 front 转角即为朝向观察者的半圈） */
const half = (r: number, side: 1 | -1) =>
  `M0 ${-r}A${r} ${r} 0 0 ${side === 1 ? 1 : 0} 0 ${r}`;

/** 往复脉冲：每个周期前 60% 从 0 平滑偏到峰值再回到 0，其余时间停在原位；相邻两次方向相反 */
const pulse = (t: number, period: number, phase = 0) => {
  const x = t / period + phase;
  const cycle = Math.floor(x);
  const p = x - cycle;
  const v = p < 0.6 ? Math.sin((Math.PI * p) / 0.6) ** 2 : 0;
  return cycle % 2 === 0 ? v : -v;
};

// 各环只在静止姿态附近的有限角度内偏移、回正，不做整圈翻转
const frame = (t: number) => {
  const a = rotX(1.02 + 0.42 * pulse(t, 13));
  const b = mul(a, rotY(0.74 + 0.5 * pulse(t, 9.5, 0.35)));
  const c = mul(b, rotX(1.0 + 0.36 * pulse(t, 7, 0.6)));
  return { a: pose(a), b: pose(b), c: pose(c) };
};

const gimbal = ref(frame(0));

let raf = 0;
onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const start = performance.now();
  const tick = (now: number) => {
    gimbal.value = frame((now - start) / 1000);
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
});
onBeforeUnmount(() => cancelAnimationFrame(raf));
</script>

<template>
  <svg class="dial" viewBox="-220 -220 440 440" fill="none" aria-hidden="true">
    <!-- 十字以外的整个仪表会被加速的推力带偏再回正；十字固定不动，作为锚点 -->
    <g class="shake">
      <!-- 机架：外刻度环缓转 + 固定承环 -->
      <g class="spin sway">
        <circle
          r="206"
          stroke="currentColor"
          stroke-opacity="0.45"
          stroke-width="8"
          stroke-dasharray="1 9.786"
        />
        <circle
          r="206"
          stroke="currentColor"
          stroke-opacity="0.9"
          stroke-width="15"
          stroke-dasharray="1.6 106.26"
        />
      </g>
      <circle r="190" stroke="currentColor" stroke-opacity="0.2" />

      <!-- 红黄绿读数弧 + 往复游标 -->
      <path
        v-for="g in gauge"
        :key="g.color"
        class="gauge"
        :d="g.d"
        :stroke="g.color"
        stroke-width="8"
        pathLength="1"
        :style="{ animationDelay: g.delay + 's' }"
      />
      <g class="needle">
        <rect x="-2" y="-199" width="4" height="18" fill="#F5EDDC" />
      </g>

      <!-- 万向环组：整体斜置 -->
      <g transform="rotate(14)">
        <!-- 外环枢轴（固定在机架上） -->
        <path
          d="M-190 0H-171M171 0H190"
          stroke="currentColor"
          stroke-opacity="0.6"
          stroke-width="3"
        />
        <rect x="-194" y="-5" width="8" height="10" fill="#F5EDDC" />
        <rect x="186" y="-5" width="8" height="10" fill="#F5EDDC" />

        <!-- 外环 -->
        <g :transform="gimbal.a.matrix">
          <g :transform="gimbal.a.front" stroke="currentColor" stroke-width="6">
            <path :d="half(168, -1)" stroke-opacity="0.22" />
          </g>
          <circle
            r="159"
            stroke="currentColor"
            stroke-opacity="0.2"
            stroke-dasharray="2 8"
          />
          <!-- 内环枢轴 -->
          <path
            d="M0 -165V-140M0 140V165"
            stroke="currentColor"
            stroke-opacity="0.6"
            stroke-width="3"
          />
        </g>

        <!-- 内环 -->
        <g :transform="gimbal.b.matrix">
          <g :transform="gimbal.b.front" stroke="currentColor" stroke-width="5">
            <path :d="half(138, -1)" stroke-opacity="0.2" />
          </g>
          <!-- 转子轴 -->
          <path
            d="M-136 0H-102M102 0H136"
            stroke="currentColor"
            stroke-opacity="0.6"
            stroke-width="3"
          />
        </g>

        <!-- 转子盘：盘面自旋 -->
        <g :transform="gimbal.c.matrix">
          <g :transform="gimbal.c.front" stroke="currentColor" stroke-width="3">
            <path :d="half(ROTOR_R, -1)" stroke-opacity="0.18" />
          </g>
          <circle
            r="62"
            stroke="currentColor"
            stroke-opacity="0.22"
            stroke-dasharray="3 6"
          />
        </g>
      </g>
    </g>

    <!-- 中心：回波与十字 -->
    <circle class="ping" r="56" stroke="#D0713C" stroke-width="1.5" />
    <circle class="ping ping-late" r="56" stroke="#D0713C" stroke-width="1.5" />
    <path d="M-10 0H10M0 -10V10" stroke="#FFFFFF" stroke-width="2" />

    <!-- 各环朝向观察者的半圈画在十字之上：先垫一圈底色，掠过中心时把十字遮住 -->
    <g class="shake">
      <g transform="rotate(14)">
        <g :transform="gimbal.c.matrix">
          <g :transform="gimbal.c.front">
            <path :d="half(ROTOR_R, 1)" class="casing" stroke-width="12" />
            <path
              :d="half(ROTOR_R, 1)"
              stroke="currentColor"
              stroke-opacity="0.6"
              stroke-width="3"
            />
          </g>
          <g class="spin comet">
            <g class="comet-trail">
              <path
                v-for="(t, i) in trail"
                :key="i"
                :d="t.d"
                stroke="#D0713C"
                :stroke-opacity="t.opacity"
                :stroke-width="t.width"
              />
            </g>
            <path
              :d="star(13)"
              :transform="`translate(0 ${-ROTOR_R})`"
              fill="#F08A4B"
            />
            <circle :cy="-ROTOR_R" r="2.2" fill="#FFF3E0" />
          </g>
        </g>
        <g :transform="gimbal.b.matrix">
          <g :transform="gimbal.b.front">
            <path :d="half(138, 1)" class="casing" stroke-width="14" />
            <path
              :d="half(138, 1)"
              stroke="currentColor"
              stroke-opacity="0.72"
              stroke-width="5"
            />
          </g>
          <circle
            r="138"
            stroke="currentColor"
            stroke-opacity="0.55"
            stroke-width="11"
            stroke-dasharray="1.4 70.86"
          />
        </g>
        <g :transform="gimbal.a.matrix">
          <g :transform="gimbal.a.front">
            <path :d="half(168, 1)" class="casing" stroke-width="15" />
            <path
              :d="half(168, 1)"
              stroke="currentColor"
              stroke-opacity="0.8"
              stroke-width="6"
            />
          </g>
          <path :d="arc(168, 20, 58)" stroke="#D0713C" stroke-width="6" />
        </g>
      </g>
    </g>
  </svg>
</template>

<style scoped>
.dial {
  display: block;
  width: 100%;
  height: 100%;
  overflow: visible;
}
.casing {
  stroke: var(--dial-backdrop, #131312);
}
.spin,
.shake,
.needle,
.ping {
  transform-origin: 0 0;
}
/* 推力偏移：缓缓偏离中心一点再回正，其余时间静止 */
.shake {
  animation: dial-shake 12s cubic-bezier(0.37, 0, 0.63, 1) infinite;
}
/* 外刻度环：小角度摆出再回正 */
.sway {
  animation: dial-sway 18s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
/* 四芒星：沿转子在一段弧内前进再退回；退回时星迹淡出，避免星迹跑到星体前方 */
.comet {
  animation: dial-comet 12s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.comet-trail {
  animation: dial-comet-trail 12s linear infinite;
}

.gauge {
  stroke-dasharray: 1;
  animation: dial-draw 0.9s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
.needle {
  transform: rotate(180deg);
  animation: dial-needle 11s cubic-bezier(0.45, 0, 0.55, 1) infinite alternate;
}
.ping {
  opacity: 0;
  animation: dial-ping 5s cubic-bezier(0.2, 0.6, 0.3, 1) infinite;
}
.ping-late {
  animation-delay: 2.5s;
}

@keyframes dial-shake {
  0%,
  22%,
  50%,
  72%,
  100% {
    transform: none;
  }
  9% {
    transform: translate(1.4px, -2.2px);
  }
  59% {
    transform: translate(-1.8px, -1.3px);
  }
}
@keyframes dial-sway {
  0%,
  15%,
  65%,
  100% {
    transform: none;
  }
  40% {
    transform: rotate(9deg);
  }
}
@keyframes dial-comet {
  0%,
  8%,
  92%,
  100% {
    transform: rotate(-20deg);
  }
  46%,
  54% {
    transform: rotate(95deg);
  }
}
@keyframes dial-comet-trail {
  0%,
  46%,
  100% {
    opacity: 1;
  }
  54%,
  92% {
    opacity: 0.15;
  }
}
@keyframes dial-draw {
  from {
    stroke-dashoffset: 1;
  }
  to {
    stroke-dashoffset: 0;
  }
}
@keyframes dial-needle {
  0% {
    transform: rotate(126deg);
  }
  38% {
    transform: rotate(200deg);
  }
  62% {
    transform: rotate(170deg);
  }
  100% {
    transform: rotate(234deg);
  }
}
@keyframes dial-ping {
  0% {
    transform: scale(0.36);
    opacity: 0.75;
  }
  70%,
  100% {
    transform: scale(1.85);
    opacity: 0;
  }
}
@media (prefers-reduced-motion: reduce) {
  .spin,
  .shake,
  .gauge,
  .needle,
  .ping {
    animation: none;
  }
}
</style>
