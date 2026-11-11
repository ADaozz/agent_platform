<script setup lang="ts">
import { computed } from 'vue'
import type { TagStyle } from '@/constants'

const props = defineProps<{
  value: string
  map: Record<string, TagStyle>
  dot?: boolean
}>()

const tag = computed<TagStyle>(
  () => props.map[props.value] ?? { label: props.value, cls: 'bg-gray-100 text-gray-600' },
)
</script>

<template>
  <span
    class="inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium whitespace-nowrap"
    :class="tag.cls"
  >
    <span v-if="dot !== false" class="h-1.5 w-1.5 rounded-full bg-current"></span>
    {{ tag.label }}
  </span>
</template>
