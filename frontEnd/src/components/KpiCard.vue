<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'
import type { IconName } from '@/icons'

defineProps<{
  title: string
  value: number | string
  icon: IconName
  suffix?: string
}>()
</script>

<template>
  <!-- 读数面板：标签在上，主读数用展示字体 -->
  <div class="card p-5">
    <div class="flex items-start justify-between">
      <span class="text-[12px] tracking-[0.08em] text-ink-muted">{{ title }}</span>
      <AppIcon :name="icon" class="!text-[18px] text-ink-faint" />
    </div>
    <div class="mt-3 flex items-baseline gap-2">
      <span class="font-display text-[40px] leading-none font-semibold tabular-nums text-ink">{{ value }}</span>
      <span v-if="suffix" class="font-mono text-xs text-ink-muted">{{ suffix }}</span>
    </div>
    <div v-if="$slots.default" class="mt-3">
      <slot />
    </div>
  </div>
</template>
