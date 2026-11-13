<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

/**
 * 陀螺仪星盘。所有部件只在固定边界内往复（偏移 → 过冲 → 回正），不做整圈旋转。
 * 固定机架（刻度环 + 三色读数弧）内是三层万向环，最底层是插槽传入的表盘背景：
 * 外环绕机架枢轴转、内环绕外环上的枢轴转、转子盘绕内环上的转子轴摆动。
 *
 * 万向环是 CSS 3D 场景：每层是一个只做 rotateX / rotateY 的平面，嵌套关系即运动学，
 * 前后遮挡（含中心十字）交给浏览器的 3D 深度排序。环面的明暗按静止姿态预先算好画进 SVG，
 * 运动只改变换矩阵，由合成线程执行，不逐帧重绘。其余会动的部件同样是各自独立、只做变换
 * 或透明度动画的图层。减少动态效果时停在静止姿态。
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

// 三色读数弧（青绿 / 黄 / 红），三段首尾相接；与表盘的 7.92 秒循环同步，每个循环在穿越星场时消失一次
const gauge = [
  { d: arc(190, 122, 160.7), color: "#6FBDAB", delay: 0.6 },
  { d: arc(190, 160.7, 199.3), color: "#FBC02C", delay: 0.35 },
  { d: arc(190, 199.3, 238), color: "#DC4538", delay: 0.1 },
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

// ── 环：主角外环最粗并带刻线，内环与转子依次收细 ──
type RingKey = "a" | "b" | "c";
const KEYS: RingKey[] = ["a", "b", "c"];
const RINGS: Record<RingKey, { r: number; width: number; count: number }> = {
  a: { r: 168, width: 9, count: 48 },
  b: { r: 138, width: 4.5, count: 40 },
  c: { r: ROTOR_R, width: 2.5, count: 32 },
};
// 相邻段略微重叠，避免抗锯齿在接缝处留下暗线
const OVERLAP = 0.004;
const segmentPaths = (r: number, n: number) =>
  Array.from({ length: n }, (_, k) => {
    const a0 = (k / n) * 2 * Math.PI - OVERLAP;
    const a1 = ((k + 1) / n) * 2 * Math.PI + OVERLAP;
    const p = (a: number) => `${(r * Math.cos(a)).toFixed(2)} ${(r * Math.sin(a)).toFixed(2)}`;
    return `M${p(a0)}A${r} ${r} 0 0 1 ${p(a1)}`;
  });

// ── 光照：光源在左上方、略朝向观察者（SVG 的 y 轴向下）──
const norm = (v: V3): V3 => {
  const l = Math.hypot(v[0], v[1], v[2]);
  return [v[0] / l, v[1] / l, v[2] / l];
};
const LIGHT = norm([-0.55, -0.7, 0.5]);
const HALFWAY = norm([LIGHT[0], LIGHT[1], LIGHT[2] + 1]);
// 整组万向环在画面中斜置 14°，打光按屏幕方向计算
const TILT = (14 * Math.PI) / 180;
/** 每段外法线在屏幕坐标中的朝向：离观察者的远近，以及受光强度 */
const shade = (m: M3, count: number) =>
  Array.from({ length: count }, (_, k) => {
    const phi = ((k + 0.5) / count) * 2 * Math.PI;
    const c = Math.cos(phi), s = Math.sin(phi);
    const x = m[0][0] * c + m[0][1] * s;
    const y = m[1][0] * c + m[1][1] * s;
    const z = m[2][0] * c + m[2][1] * s;
    const sx = x * Math.cos(TILT) - y * Math.sin(TILT);
    const sy = x * Math.sin(TILT) + y * Math.cos(TILT);
    const diffuse = Math.max(0, sx * LIGHT[0] + sy * LIGHT[1] + z * LIGHT[2]);
    const specular = Math.max(0, sx * HALFWAY[0] + sy * HALFWAY[1] + z * HALFWAY[2]) ** 24;
    return { depth: z, light: Math.min(1, 0.12 + 0.55 * diffuse + 0.9 * specular) };
  });

// ── 运动：每次推动是一个欠阻尼弹簧的冲击响应——快速偏出、轻微过冲、再稳住 ──
const ZETA = 0.42;
const OMEGA = 12;
const springShape = (u: number) =>
  Math.exp(-ZETA * OMEGA * u) * Math.sin(OMEGA * Math.sqrt(1 - ZETA * ZETA) * u) * (1 - u ** 6);
const SPRING_PEAK = Math.max(...Array.from({ length: 400 }, (_, i) => springShape(i / 400)));
/** 每个周期前 60% 是一次推动及回正，其余时间静止；相邻两次方向相反 */
const kick = (t: number, period: number, phase = 0) => {
  const x = t / period + phase;
  const cycle = Math.floor(x);
  const p = x - cycle;
  const v = p < 0.6 ? springShape(p / 0.6) / SPRING_PEAK : 0;
  return { value: cycle % 2 === 0 ? v : -v, cycle };
};

// 各环绕自己的轴在静止姿态附近摆动：外环 X、内环 Y、转子 X
const MOTION: Record<RingKey, { axis: "X" | "Y"; rest: number; amp: number; period: number; phase: number }> = {
  a: { axis: "X", rest: 1.02, amp: 0.36, period: 13, phase: 0 },
  b: { axis: "Y", rest: 0.74, amp: 0.42, period: 9.5, phase: 0.35 },
  c: { axis: "X", rest: 1.0, amp: 0.3, period: 7, phase: 0.6 },
};
const rotation = (key: RingKey, angle: number) => `rotate${MOTION[key].axis}(${angle.toFixed(4)}rad)`;
const restTransform = Object.fromEntries(KEYS.map((key) => [key, rotation(key, MOTION[key].rest)])) as Record<RingKey, string>;

// 静止姿态下各环的世界朝向，用于预先打光
const restMats = (() => {
  const a = rotX(MOTION.a.rest);
  const b = mul(a, rotY(MOTION.b.rest));
  const c = mul(b, rotX(MOTION.c.rest));
  return { a, b, c } as Record<RingKey, M3>;
})();
// 环面是不透明的：亮度混合到表盘底色上，前后半圈之间平滑过渡
const IVORY: V3 = [242, 234, 217];
const BACKDROP: V3 = [11, 14, 15];
const paint = (opacity: number) =>
  `rgb(${IVORY.map((c, i) => Math.round(BACKDROP[i]! + (c - BACKDROP[i]!) * opacity * 0.92)).join(" ")})`;
const bands = Object.fromEntries(
  KEYS.map((key) => {
    const paths = segmentPaths(RINGS[key].r, RINGS[key].count);
    return [
      key,
      shade(restMats[key], RINGS[key].count).map(({ depth, light }, k) => {
        const t = Math.min(1, Math.max(0, (depth + 0.18) / 0.36));
        const blend = t * t * (3 - 2 * t);
        const opacity = (0.06 + 0.3 * light) * (1 - blend) + (0.26 + 0.74 * light) * blend;
        return { d: paths[k], color: paint(opacity), front: depth >= 0 };
      }),
    ];
  }),
) as Record<RingKey, { d: string; color: string; front: boolean }[]>;
// 外环表面的刻线，一段一根，只刻在朝向观察者的一侧
const ticks = bands.a
  .map((segment, k) => {
    const a = (k / RINGS.a.count) * 2 * Math.PI;
    const p = (r: number) => `${(r * Math.cos(a)).toFixed(2)} ${(r * Math.sin(a)).toFixed(2)}`;
    return segment.front ? `M${p(RINGS.a.r - 2.8)}L${p(RINGS.a.r + 2.8)}` : "";
  })
  .filter(Boolean);

/** 两个周期（一正一反两次推动）的关键帧，按弹簧响应采样 */
const keyframes = (key: RingKey) => {
  const { rest, amp, period } = MOTION[key];
  const steps = 160;
  return Array.from({ length: steps + 1 }, (_, i) => {
    const offset = i / steps;
    return { offset, transform: rotation(key, rest + amp * kick(offset * 2 * period, period).value) };
  });
};

// 外环当前的倾角（度），交给表盘背景显示；外环每被推动一次，固定的十字发出一圈回波
const degrees = (rad: number) => Math.round((rad * 180) / Math.PI);
const angle = ref(degrees(MOTION.a.rest));
const pingKey = ref(0);

const frames: Record<RingKey, HTMLElement | null> = { a: null, b: null, c: null };
const bindFrame = (key: RingKey) => (el: unknown) => {
  frames[key] = el as HTMLElement | null;
};
const animations: Animation[] = [];
let raf = 0;
onMounted(() => {
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  for (const key of KEYS) {
    const { period, phase } = MOTION[key];
    const el = frames[key];
    if (!el) continue;
    animations.push(el.animate(keyframes(key), { duration: 2 * period * 1000, delay: -phase * period * 1000, iterations: Infinity, easing: "linear" }));
  }
  const start = performance.now();
  let lastCycle = -1;
  // 只做数学运算；整数度数或推动周期变化时才触发渲染
  const tick = (now: number) => {
    const outer = kick((now - start) / 1000, MOTION.a.period);
    const tilt = degrees(MOTION.a.rest + MOTION.a.amp * outer.value);
    if (tilt !== angle.value) angle.value = tilt;
    if (outer.cycle !== lastCycle) {
      lastCycle = outer.cycle;
      pingKey.value += 1;
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
});
onBeforeUnmount(() => {
  cancelAnimationFrame(raf);
  animations.forEach((animation) => animation.cancel());
});
</script>

<template>
  <!-- 自下而上：表盘背景（插槽）→ 机架 → 万向环 3D 场景（含十字）→ 回波 -->
  <div class="dial-stack" aria-hidden="true">
    <div class="dial-core shake"><slot :angle="angle" /></div>

    <!-- 机架：整体随推力偏移再回正 -->
    <div class="layer-group shake">
      <svg class="layer" style="--r: 192" viewBox="-192 -192 384 384" fill="none">
        <circle r="190" stroke="currentColor" stroke-opacity="0.12" />
        <g transform="rotate(14)">
          <path d="M-190 0H-173M173 0H190" stroke="currentColor" stroke-opacity="0.45" stroke-width="3" />
          <rect x="-194" y="-5" width="8" height="10" fill="#F5EDDC" />
          <rect x="186" y="-5" width="8" height="10" fill="#F5EDDC" />
        </g>
      </svg>
      <!-- 外刻度环：小角度摆出再回正 -->
      <svg class="layer sway" style="--r: 214" viewBox="-214 -214 428 428" fill="none">
        <circle r="206" stroke="currentColor" stroke-opacity="0.28" stroke-width="8" stroke-dasharray="1 9.786" />
        <circle r="206" stroke="currentColor" stroke-opacity="0.55" stroke-width="15" stroke-dasharray="1.6 106.26" />
      </svg>
      <svg class="layer gauge" style="--r: 196" viewBox="-196 -196 392 392" fill="none">
        <path
          v-for="g in gauge"
          :key="g.color"
          :d="g.d"
          :stroke="g.color"
          stroke-width="10"
          pathLength="1"
          :style="{ animationDelay: `${g.delay}s` }"
        />
      </svg>
      <svg class="layer needle" style="--r: 200" viewBox="-200 -200 400 400" fill="none">
        <rect x="-2" y="-199" width="4" height="18" fill="#F5EDDC" />
      </svg>
    </div>

    <!-- 万向环：3D 场景，整组斜置 14° -->
    <div class="gimbal">
      <svg class="layer cross" style="--r: 11" viewBox="-11 -11 22 22" fill="none">
        <path d="M-10 0H10M0 -10V10" stroke="#FFFFFF" stroke-width="2" />
      </svg>
      <div class="frame shake">
        <div :ref="bindFrame('a')" class="frame" :style="{ transform: restTransform.a }">
          <svg class="layer" style="--r: 176" viewBox="-176 -176 352 352" fill="none">
            <path v-for="(s, k) in bands.a" :key="k" :d="s.d" :stroke="s.color" :stroke-width="RINGS.a.width" />
            <!-- 刻在外环表面的细线，与外缘一圈加工棱线 -->
            <path v-for="(d, k) in ticks" :key="'tick' + k" :d="d" :stroke="paint(0)" stroke-opacity="0.6" stroke-width="0.9" />
            <circle :r="RINGS.a.r + RINGS.a.width / 2 + 1.2" stroke="currentColor" stroke-opacity="0.1" stroke-width="0.8" />
            <path :d="arc(RINGS.a.r, 20, 58)" stroke="#F36B18" :stroke-width="RINGS.a.width" stroke-opacity="0.9" />
            <!-- 内环枢轴 -->
            <path d="M0 -163V-141M0 141V163" stroke="currentColor" stroke-opacity="0.45" stroke-width="3" />
          </svg>
          <div :ref="bindFrame('b')" class="frame" :style="{ transform: restTransform.b }">
            <svg class="layer" style="--r: 144" viewBox="-144 -144 288 288" fill="none">
              <path v-for="(s, k) in bands.b" :key="k" :d="s.d" :stroke="s.color" :stroke-width="RINGS.b.width" />
              <circle :r="RINGS.b.r" stroke="currentColor" stroke-opacity="0.35" stroke-width="10" stroke-dasharray="1.4 70.86" />
              <!-- 转子轴 -->
              <path d="M-135 0H-102M102 0H135" stroke="currentColor" stroke-opacity="0.45" stroke-width="3" />
            </svg>
            <div :ref="bindFrame('c')" class="frame" :style="{ transform: restTransform.c }">
              <svg class="layer" style="--r: 102" viewBox="-102 -102 204 204" fill="none">
                <path v-for="(s, k) in bands.c" :key="k" :d="s.d" :stroke="s.color" :stroke-width="RINGS.c.width" />
              </svg>
              <!-- 四芒星：沿转子在一段弧内前进再退回 -->
              <svg class="layer comet" style="--r: 116" viewBox="-116 -116 232 232" fill="none">
                <g class="comet-trail">
                  <path v-for="(t, i) in trail" :key="i" :d="t.d" stroke="#F36B18" :stroke-opacity="t.opacity" :stroke-width="t.width" />
                </g>
                <path :d="star(13)" :transform="`translate(0 ${-ROTOR_R})`" fill="#F36B18" />
                <circle :cy="-ROTOR_R" r="2.2" fill="#FFF3E0" />
              </svg>
            </div>
          </div>
        </div>
      </div>
    </div>

    <div v-if="pingKey" :key="pingKey" class="ping"></div>
  </div>
</template>

<style scoped>
.dial-stack {
  position: relative;
  width: 100%;
  height: 100%;
}
.dial-core,
.layer-group,
.gimbal,
.frame {
  position: absolute;
  inset: 0;
}
/* 以星盘中心为原点、半径 --r（SVG 用户单位，全盘 440）摆放的图层 */
.layer {
  position: absolute;
  left: calc((220 - var(--r)) / 440 * 100%);
  top: calc((220 - var(--r)) / 440 * 100%);
  width: calc(var(--r) / 220 * 100%);
  height: calc(var(--r) / 220 * 100%);
  overflow: visible;
}
/* 3D 场景：中间每一层都要保持 3D，叶子图层才能互相按深度排序 */
.gimbal {
  transform: rotate(14deg);
  transform-style: preserve-3d;
}
.frame {
  transform-style: preserve-3d;
}
/* 十字是锚点：不随整组斜置，也不随推力偏移 */
.cross {
  transform: rotate(-14deg);
}

/* 推力偏移：缓缓偏离中心一点再回正，其余时间静止 */
.shake {
  animation: instrument-shake 12s cubic-bezier(0.37, 0, 0.63, 1) infinite;
}
.sway {
  animation: dial-sway 18s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.needle {
  transform: rotate(180deg);
  animation: dial-needle 11s cubic-bezier(0.45, 0, 0.55, 1) infinite alternate;
}
.gauge {
  animation: meter-cycle 7.92s ease-in-out infinite;
}
.gauge path {
  stroke-dasharray: 1;
  animation: dial-draw 0.9s cubic-bezier(0.2, 0.7, 0.2, 1) both;
}
/* 退回时星迹淡出，避免星迹跑到星体前方 */
.comet {
  animation: dial-comet 12s cubic-bezier(0.45, 0, 0.55, 1) infinite;
}
.comet-trail {
  animation: dial-comet-trail 12s linear infinite;
}
/* 每次推动发出一圈，重新挂载即重新播放 */
.ping {
  position: absolute;
  left: 37.27%;
  top: 37.27%;
  width: 25.45%;
  height: 25.45%;
  border: 1.5px solid #f36b18;
  border-radius: 50%;
  opacity: 0;
  animation: dial-ping 2.6s cubic-bezier(0.2, 0.6, 0.3, 1) both;
}

@keyframes instrument-shake {
  0%,
  22%,
  50%,
  72%,
  100% {
    translate: none;
  }
  9% {
    translate: 0.32% -0.5%;
  }
  59% {
    translate: -0.41% -0.3%;
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
@keyframes meter-cycle {
  0%,
  19% {
    opacity: 1;
  }
  30%,
  64% {
    opacity: 0;
  }
  73%,
  100% {
    opacity: 1;
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
  .shake,
  .sway,
  .needle,
  .gauge,
  .gauge path,
  .comet,
  .comet-trail,
  .ping {
    animation: none;
  }
}
</style>
