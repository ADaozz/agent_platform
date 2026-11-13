<script setup lang="ts">
/** 字标中间“三色条 + A”的纯 CSS 方形版，用于收起侧栏等小尺寸场景 */
defineProps<{ size?: number }>()
</script>

<template>
  <span class="brand-glyph" role="img" aria-label="Deep Agent" :style="{ '--glyph-size': `${size ?? 30}px` }">
    <span class="brand-glyph-a" aria-hidden="true"></span>
  </span>
</template>

<style scoped>
.brand-glyph {
  position: relative;
  display: block;
  flex-shrink: 0;
  width: var(--glyph-size);
  height: var(--glyph-size);
  background: linear-gradient(90deg, #41cbb5 0 33.34%, #fcbe08 0 66.67%, #e73c2a 0);
  box-shadow: inset 0 0 0 1px rgb(0 0 0 / 0.12);
}
.brand-glyph::after {
  content: '';
  position: absolute;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(0deg, rgb(255 255 255 / 0.05) 0 1px, transparent 1px 3px);
}
.brand-glyph-a {
  position: absolute;
  inset: 0;
  /* 红色错版描边在左上，压暗阴影在右下，对应字标的复古套印效果 */
  filter: drop-shadow(-1px -1px 0 #e73c2a) drop-shadow(1.5px 1.5px 0 rgb(8 32 30 / 0.6));
}
.brand-glyph-a::before {
  content: '';
  position: absolute;
  inset: 0;
  background: #f5ecd0;
  clip-path: polygon(15% 86%, 64.8% 14%, 85% 14%, 85% 86%, 66.6% 86%, 66.6% 42.6%, 37% 86%);
}
</style>
