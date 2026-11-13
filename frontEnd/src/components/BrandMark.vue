<script setup lang="ts">
import wordmark from '@/assets/deep-agent-wordmark.webp'

/** size 为字标高度（px），宽度按原图比例 */
defineProps<{ size?: number }>()
</script>

<template>
  <img
    :src="wordmark"
    alt="Deep Agent"
    class="brand-mark"
    :style="{ height: `${size ?? 32}px` }"
    draggable="false"
  />
</template>

<style scoped>
.brand-mark {
  display: block;
  max-width: none;
  user-select: none;
}
</style>
