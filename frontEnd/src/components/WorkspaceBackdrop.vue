<template>
  <!-- Zero-height, inert decoration: the workspace keeps all of its existing geometry. -->
  <div class="workspace-backdrop" aria-hidden="true" inert>
    <div class="workspace-backdrop-stage">
      <div class="workspace-backdrop-orbits"></div>
      <span class="workspace-backdrop-cross cross-left"></span>
      <span class="workspace-backdrop-cross cross-right"></span>
      <span class="workspace-backdrop-hatching"></span>
      <div class="workspace-backdrop-head">
        <span class="workspace-backdrop-name">DEEP AGENT</span>
        <span class="workspace-backdrop-rule"></span>
        <span class="workspace-backdrop-technical">AGENT WORKSPACE / SYSTEM ONLINE</span>
        <span class="workspace-backdrop-dots"></span>
      </div>
      <div class="workspace-backdrop-foot">
        <span class="workspace-backdrop-name">DEEP AGENT</span>
        <span class="workspace-backdrop-rule"></span>
        <span class="workspace-backdrop-signals"></span>
        <span class="workspace-backdrop-technical">INTELLIGENCE / EXECUTION / WORKSPACE</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.workspace-backdrop {
  position: sticky;
  top: 0;
  height: 0;
  margin-inline-end: calc(-1 * var(--ws-backdrop-gutter, 0px));
  z-index: -1;
  pointer-events: none;
  user-select: none;
}
.workspace-backdrop-stage {
  --orbit-line: rgb(154 125 77 / 0.18);
  --orbit-band: rgb(174 133 79 / 0.2);
  --orbit-glow: rgb(243 107 24 / 0.13);
  --orbit-ink: #706553;
  --orbit-cross: rgb(154 125 77 / 0.55);
  position: absolute;
  inset-inline: 0;
  top: var(--ws-backdrop-top, 0px);
  height: calc(var(--dap-vh) - var(--ws-backdrop-top, 0px) - var(--ws-backdrop-bottom, 0px));
  container-type: size;
  overflow: hidden;
  pointer-events: none;
  color: var(--orbit-ink);
  background:
    radial-gradient(ellipse 62% 46% at 94% 0%, var(--orbit-glow), transparent 76%),
    radial-gradient(ellipse 38% 22% at 0% 100%, rgb(223 169 60 / 0.045), transparent 80%),
    var(--color-page);
}
:global(.agent-host[data-theme='dark'] .workspace-backdrop-stage) {
  --orbit-line: rgb(149 138 120 / 0.13);
  --orbit-band: rgb(149 138 120 / 0.16);
  --orbit-glow: rgb(178 70 15 / 0.16);
  --orbit-ink: #958a78;
  --orbit-cross: rgb(149 138 120 / 0.4);
}
/* Each orbit is a circle with equal axes, anchored to an edge of the live container. */
.workspace-backdrop-stage::before,
.workspace-backdrop-stage::after,
.workspace-backdrop-orbits::before,
.workspace-backdrop-orbits::after {
  content: '';
  position: absolute;
  aspect-ratio: 1;
  border-radius: 50%;
  background: repeating-radial-gradient(circle, transparent 0 25px, var(--orbit-line) 25px 26px, transparent 26px 52px);
  mask-image: radial-gradient(circle, transparent 0 32%, #000 40% 60%, transparent 71%);
}
.workspace-backdrop-stage::before {
  width: clamp(18rem, 67cqi, 58rem);
  top: 0;
  right: 0;
  transform: translate(20%, -30%);
}
.workspace-backdrop-stage::after {
  width: clamp(15rem, 52cqi, 42rem);
  left: 0;
  bottom: 0;
  transform: translate(-46%, 49%);
  background:
    radial-gradient(circle, transparent 0 48%, var(--orbit-band) 48% 51%, transparent 51%),
    repeating-radial-gradient(circle, transparent 0 19px, var(--orbit-line) 19px 20px, transparent 20px 39px);
}
.workspace-backdrop-orbits::before {
  width: clamp(12rem, 35cqi, 30rem);
  left: 0;
  top: 40%;
  transform: translateX(-76%);
}
.workspace-backdrop-orbits::after {
  width: clamp(14rem, 40cqi, 34rem);
  right: 0;
  bottom: 16%;
  transform: translate(73%, 40%);
}
.workspace-backdrop-cross {
  position: absolute;
  width: clamp(14px, 2.7cqi, 28px);
  aspect-ratio: 1;
  background:
    radial-gradient(circle, var(--orbit-cross) 0 2px, transparent 2.5px),
    linear-gradient(var(--orbit-cross), var(--orbit-cross)) center / 1px 100% no-repeat,
    linear-gradient(var(--orbit-cross), var(--orbit-cross)) center / 100% 1px no-repeat;
  opacity: 0.65;
}
.cross-left { left: 9%; top: 65%; }
.cross-right { right: 10%; top: 43%; }
.workspace-backdrop-hatching {
  position: absolute;
  right: 3%;
  bottom: 5%;
  width: clamp(36px, 10cqi, 130px);
  height: clamp(10px, 2.5cqi, 28px);
  background: repeating-linear-gradient(-48deg, transparent 0 7px, var(--orbit-band) 7px 20px, transparent 20px 26px);
}
.workspace-backdrop-head,
.workspace-backdrop-foot {
  position: absolute;
  inset-inline: 0;
  display: flex;
  align-items: center;
  gap: clamp(3px, 1.3cqi, 18px);
  padding-inline: clamp(6px, 2.4cqi, 32px);
  overflow: hidden;
  white-space: nowrap;
  line-height: 1;
}
.workspace-backdrop-head {
  top: 0;
  height: 24px;
  font-size: clamp(6px, 0.8cqi, 10px);
}
.workspace-backdrop-foot {
  bottom: 0;
  height: 14px;
  border-top: 1px solid var(--orbit-line);
  background: var(--color-panel);
  color: var(--color-ivory);
  font-size: clamp(5px, 0.58cqi, 8px);
}
.workspace-backdrop-name,
.workspace-backdrop-technical {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.workspace-backdrop-name {
  max-width: 32%;
  font-weight: 700;
  letter-spacing: 0.09em;
  flex-shrink: 1;
}
.workspace-backdrop-head .workspace-backdrop-name::before {
  content: '';
  display: inline-block;
  width: clamp(8px, 2.5cqi, 34px);
  height: 1em;
  margin-right: clamp(3px, 1cqi, 12px);
  vertical-align: -0.1em;
  background: repeating-linear-gradient(-55deg, transparent 0 3px, var(--color-signal) 3px 7px, transparent 7px 9px);
}
.workspace-backdrop-rule {
  flex: 1 1 8%;
  min-width: 0;
  height: 1px;
  background: currentColor;
  opacity: 0.42;
}
.workspace-backdrop-technical {
  max-width: 61%;
  font-family: var(--font-mono);
  letter-spacing: 0.1em;
}
.workspace-backdrop-dots {
  flex: 0 0 clamp(6px, 1.3cqi, 14px);
  aspect-ratio: 1;
  background: radial-gradient(circle, currentColor 0 35%, transparent 40%) 0 0 / 50% 50%;
  opacity: 0.6;
}
.workspace-backdrop-signals {
  flex: 0 0 clamp(12px, 3.5cqi, 42px);
  height: clamp(3px, 0.65cqi, 7px);
  background: linear-gradient(90deg,
    var(--color-tri-red) 0 23%, transparent 23% 38%,
    var(--color-tri-yellow) 38% 61%, transparent 61% 76%,
    var(--color-tri-green) 76%);
}
@container (max-width: 480px) {
  .workspace-backdrop-stage::before { width: 88cqi; }
  .workspace-backdrop-stage::after { width: 78cqi; }
  .workspace-backdrop-cross { opacity: 0.35; }
  .workspace-backdrop-technical { letter-spacing: 0.04em; }
}
</style>
