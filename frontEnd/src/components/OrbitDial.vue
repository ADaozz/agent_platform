<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

/**
 * 陀螺仪星盘：纯 SVG。所有部件只在固定边界内往复（偏移 → 过冲 → 回正），不做整圈旋转。
 * 固定机架（刻度环 + 红黄绿读数弧）内是三层万向环：
 * 外环绕机架枢轴转、内环绕外环上的枢轴转、转子盘绕内环上的转子轴摆动。
 * 每层的姿态是真实的三维旋转 Rx(α)·Ry(β)·Rx(γ)，正投影后写成 SVG matrix。
 * 环被切成若干小段，按各段在三维中的朝向逐段打光（漫反射 + 高光），
 * 朝向观察者的段画在十字之上并垫底色遮挡，背向的段画在十字之下并压暗。
 * 减少动态效果时停在一个固定姿态。
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
/** 环所在平面的正投影矩阵 */
const matrix = (m: M3) =>
  `matrix(${f(m[0][0])} ${f(m[1][0])} ${f(m[0][1])} ${f(m[1][1])} 0 0)`;

// ── 环：主角外环最粗并带刻线，内环与转子依次收细 ──
type RingKey = "a" | "b" | "c";
const KEYS: RingKey[] = ["a", "b", "c"];
// 朝向观察者的一侧由内向外叠放，外环在最上层
const FRONT_ORDER: RingKey[] = ["c", "b", "a"];
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
const segments = Object.fromEntries(
  KEYS.map((key) => [key, segmentPaths(RINGS[key].r, RINGS[key].count)]),
) as Record<RingKey, string[]>;
// 外环表面的刻线，一段一根
const ticks = Array.from({ length: RINGS.a.count }, (_, k) => {
  const a = (k / RINGS.a.count) * 2 * Math.PI;
  const p = (r: number) => `${(r * Math.cos(a)).toFixed(2)} ${(r * Math.sin(a)).toFixed(2)}`;
  return `M${p(RINGS.a.r - 2.8)}L${p(RINGS.a.r + 2.8)}`;
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
/** 每段外法线在屏幕坐标中的朝向：是否朝向观察者，以及受光强度 */
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
    return { front: z >= 0, depth: z, light: Math.min(1, 0.12 + 0.55 * diffuse + 0.9 * specular) };
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

const frame = (t: number) => {
  const outer = kick(t, 13);
  const a = rotX(1.02 + 0.36 * outer.value);
  const b = mul(a, rotY(0.74 + 0.42 * kick(t, 9.5, 0.35).value));
  const c = mul(b, rotX(1.0 + 0.3 * kick(t, 7, 0.6).value));
  return { mats: { a, b, c } as Record<RingKey, M3>, cycle: outer.cycle };
};

const initial = frame(0);
const gimbal = ref(
  Object.fromEntries(KEYS.map((key) => [key, matrix(initial.mats[key])])) as Record<RingKey, string>,
);
// 外环每被推动一次，固定的十字发出一圈回波
const pingKey = ref(0);

const root = ref<SVGSVGElement | null>(null);
type Layer = "back" | "casing" | "front" | "tick";
let nodes: Record<string, Element[]> = {};
const collect = () => {
  nodes = {};
  root.value?.querySelectorAll("[data-ring]").forEach((node) => {
    const key = `${node.getAttribute("data-ring")}:${node.getAttribute("data-layer")}`;
    (nodes[key] ??= []).push(node);
  });
};
const set = (key: RingKey, layer: Layer, k: number, value: string) =>
  nodes[`${key}:${layer}`]?.[k]?.setAttribute("stroke-opacity", value);
/** 逐段写入亮度；每帧几百个属性，直接改 DOM，不经过 Vue 的响应式渲染 */
const paint = (mats: Record<RingKey, M3>) => {
  for (const key of KEYS) {
    shade(mats[key], RINGS[key].count).forEach(({ front, depth, light }, k) => {
      // Near the silhouette the ring turns edge-on; blend so front and back meet without a step.
      const t = Math.min(1, Math.max(0, (depth + 0.18) / 0.36));
      const blend = t * t * (3 - 2 * t);
      const opacity = (0.06 + 0.3 * light) * (1 - blend) + (0.26 + 0.74 * light) * blend;
      set(key, "back", k, front ? "0" : opacity.toFixed(3));
      set(key, "casing", k, front ? "1" : "0");
      set(key, "front", k, front ? opacity.toFixed(3) : "0");
      if (key === "a") set(key, "tick", k, front ? "0.6" : "0");
    });
  }
};

let raf = 0;
onMounted(() => {
  collect();
  paint(initial.mats);
  if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const start = performance.now();
  let lastCycle = -1;
  const tick = (now: number) => {
    const next = frame((now - start) / 1000);
    gimbal.value = Object.fromEntries(KEYS.map((key) => [key, matrix(next.mats[key])])) as Record<RingKey, string>;
    paint(next.mats);
    if (next.cycle !== lastCycle) {
      lastCycle = next.cycle;
      pingKey.value += 1;
    }
    raf = requestAnimationFrame(tick);
  };
  raf = requestAnimationFrame(tick);
});
onBeforeUnmount(() => cancelAnimationFrame(raf));
</script>

<template>
  <svg ref="root" class="dial" viewBox="-220 -220 440 440" fill="none" aria-hidden="true">
    <!-- 十字以外的整个仪表会被加速的推力带偏再回正；十字固定不动，作为锚点 -->
    <g class="shake">
      <!-- 机架：外刻度环摆动 + 固定承环，整体压暗，让万向外环成为主角 -->
      <g class="spin sway">
        <circle r="206" stroke="currentColor" stroke-opacity="0.28" stroke-width="8" stroke-dasharray="1 9.786" />
        <circle r="206" stroke="currentColor" stroke-opacity="0.55" stroke-width="15" stroke-dasharray="1.6 106.26" />
      </g>
      <circle r="190" stroke="currentColor" stroke-opacity="0.12" />

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

      <!-- 万向环组：整体斜置；这里画各环背向观察者的段 -->
      <g transform="rotate(14)">
        <!-- 外环枢轴（固定在机架上） -->
        <path d="M-190 0H-173M173 0H190" stroke="currentColor" stroke-opacity="0.45" stroke-width="3" />
        <rect x="-194" y="-5" width="8" height="10" fill="#F5EDDC" />
        <rect x="186" y="-5" width="8" height="10" fill="#F5EDDC" />

        <g v-for="key in KEYS" :key="key" :transform="gimbal[key]">
          <path
            v-for="(d, k) in segments[key]"
            :key="k"
            :d="d"
            :data-ring="key"
            data-layer="back"
            stroke="currentColor"
            :stroke-width="RINGS[key].width"
            stroke-opacity="0.12"
          />
          <!-- 内环枢轴 / 转子轴 -->
          <path v-if="key === 'a'" d="M0 -163V-141M0 141V163" stroke="currentColor" stroke-opacity="0.45" stroke-width="3" />
          <path v-if="key === 'b'" d="M-135 0H-102M102 0H135" stroke="currentColor" stroke-opacity="0.45" stroke-width="3" />
          <circle v-if="key === 'c'" r="62" stroke="currentColor" stroke-opacity="0.14" stroke-dasharray="3 6" />
        </g>
      </g>
    </g>

    <!-- 中心：回波与十字 -->
    <circle v-if="pingKey" :key="pingKey" class="ping" r="56" stroke="#D0713C" stroke-width="1.5" />
    <path d="M-10 0H10M0 -10V10" stroke="#FFFFFF" stroke-width="2" />

    <!-- 各环朝向观察者的段画在十字之上：先垫一层底色，掠过中心时把十字遮住 -->
    <g class="shake">
      <g transform="rotate(14)">
        <g v-for="key in FRONT_ORDER" :key="key" :transform="gimbal[key]">
          <path
            v-for="(d, k) in segments[key]"
            :key="'casing' + k"
            :d="d"
            :data-ring="key"
            data-layer="casing"
            class="casing"
            :stroke-width="RINGS[key].width + 8"
            stroke-opacity="0"
          />
          <path
            v-for="(d, k) in segments[key]"
            :key="'front' + k"
            :d="d"
            :data-ring="key"
            data-layer="front"
            stroke="currentColor"
            :stroke-width="RINGS[key].width"
            stroke-opacity="0"
          />
          <template v-if="key === 'a'">
            <!-- 刻在外环表面的细线，与外缘一圈加工棱线 -->
            <path
              v-for="(d, k) in ticks"
              :key="'tick' + k"
              :d="d"
              :data-ring="key"
              data-layer="tick"
              class="casing"
              stroke-width="0.9"
              stroke-opacity="0"
            />
            <circle :r="RINGS.a.r + RINGS.a.width / 2 + 1.2" stroke="currentColor" stroke-opacity="0.1" stroke-width="0.8" />
            <path :d="arc(RINGS.a.r, 20, 58)" stroke="#D0713C" :stroke-width="RINGS.a.width" stroke-opacity="0.9" />
          </template>
          <circle v-if="key === 'b'" :r="RINGS.b.r" stroke="currentColor" stroke-opacity="0.35" stroke-width="10" stroke-dasharray="1.4 70.86" />
          <g v-if="key === 'c'" class="spin comet">
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
            <path :d="star(13)" :transform="`translate(0 ${-ROTOR_R})`" fill="#F08A4B" />
            <circle :cy="-ROTOR_R" r="2.2" fill="#FFF3E0" />
          </g>
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
/* 每次推动发出一圈，重新挂载即重新播放 */
.ping {
  opacity: 0;
  animation: dial-ping 2.6s cubic-bezier(0.2, 0.6, 0.3, 1) both;
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
