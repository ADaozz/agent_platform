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
  <div class="card p-5">
    <div class="flex items-start justify-between">
      <span class="text-sm text-ink-muted">{{ title }}</span>
      <AppIcon :name="icon" class="text-ink-faint" />
    </div>
    <div class="mt-2 flex items-baseline gap-2">
      <span class="text-3xl font-semibold tracking-tight text-ink">{{ value }}</span>
      <span v-if="suffix" class="text-sm text-ink-muted">{{ suffix }}</span>
    </div>
    <div v-if="$slots.default" class="mt-3">
      <slot />
    </div>
  </div>
</template>
