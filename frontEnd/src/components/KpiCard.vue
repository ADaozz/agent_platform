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
  <div class="@container card p-4 sm:p-5">
    <div class="flex items-start justify-between">
      <span class="text-[12px] tracking-[0.08em] text-ink-muted">{{ title }}</span>
      <AppIcon :name="icon" class="!text-[18px] text-ink-faint" />
    </div>
    <div class="mt-3 flex flex-wrap items-baseline gap-x-2 gap-y-1">
      <span class="font-display text-[clamp(26px,18cqi,40px)] leading-none font-semibold tabular-nums text-ink">{{ value }}</span>
      <span v-if="suffix" class="font-mono text-xs whitespace-nowrap text-ink-muted">{{ suffix }}</span>
    </div>
    <div v-if="$slots.default" class="mt-3">
      <slot />
    </div>
  </div>
</template>
