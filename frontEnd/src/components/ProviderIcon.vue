<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
const props = withDefaults(defineProps<{ provider: string; size?: number }>(), { size: 32 })
const icons: Record<string, string> = { deepseek: '/providers/deepseek.svg', qwen: '/providers/qwen.svg', glm: '/providers/glm.png' }
const icon = computed(() => icons[props.provider.toLowerCase()])
</script>

<template>
  <span class="provider-avatar" :style="{ '--provider-icon-size': `${size}px` }" aria-hidden="true">
    <img v-if="icon" :src="icon" alt="" />
    <AppIcon v-else name="dns" />
  </span>
</template>

<style scoped>
.provider-avatar { display: inline-flex; align-items: center; justify-content: center; flex: 0 0 var(--provider-icon-size); width: var(--provider-icon-size); height: var(--provider-icon-size); }
.provider-avatar img { display: block; width: 100%; height: 100%; object-fit: contain; }
.provider-avatar .app-icon { width: 75%; height: 75%; color: var(--color-ink-muted); }
</style>
