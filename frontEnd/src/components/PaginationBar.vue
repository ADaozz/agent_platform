<script setup lang="ts">
import { computed } from 'vue'
import AppIcon from '@/components/AppIcon.vue'

const props = defineProps<{
  total: number
  pageNum: number
  pageSize: number
}>()

const emit = defineEmits<{ change: [pageNum: number] }>()

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

const pages = computed<(number | '...')[]>(() => {
  const tp = totalPages.value
  const cur = props.pageNum
  if (tp <= 7) return Array.from({ length: tp }, (_, i) => i + 1)
  const result: (number | '...')[] = [1]
  if (cur > 3) result.push('...')
  for (let p = Math.max(2, cur - 1); p <= Math.min(tp - 1, cur + 1); p++) result.push(p)
  if (cur < tp - 2) result.push('...')
  result.push(tp)
  return result
})

function go(p: number) {
  if (p < 1 || p > totalPages.value || p === props.pageNum) return
  emit('change', p)
}
</script>

<template>
  <div class="flex items-center justify-between px-4 py-3">
    <span class="text-sm text-ink-muted">
      共 {{ total }} 条记录
    </span>
    <div class="flex items-center gap-1">
      <button
        class="flex h-8 w-8 items-center justify-center rounded-md border border-line text-ink-secondary transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="pageNum <= 1"
        @click="go(pageNum - 1)"
      >
        <AppIcon name="chevron_left" class="!text-[18px]" />
      </button>
      <template v-for="(p, i) in pages" :key="i">
        <span v-if="p === '...'" class="px-1.5 text-sm text-ink-faint">…</span>
        <button
          v-else
          class="h-8 min-w-8 rounded-md px-2 text-sm transition-colors"
          :class="p === pageNum ? 'bg-primary font-medium text-white' : 'border border-line text-ink-secondary hover:bg-gray-50'"
          @click="go(p)"
        >
          {{ p }}
        </button>
      </template>
      <button
        class="flex h-8 w-8 items-center justify-center rounded-md border border-line text-ink-secondary transition-colors hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-40"
        :disabled="pageNum >= totalPages"
        @click="go(pageNum + 1)"
      >
        <AppIcon name="chevron_right" class="!text-[18px]" />
      </button>
    </div>
  </div>
</template>
