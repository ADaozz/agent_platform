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
  <div class="flex items-center justify-between gap-3 border-t border-line px-4 py-3">
    <span class="font-mono text-[11px] tracking-[0.1em] text-ink-faint">
      共 <span class="text-ink-secondary tabular-nums">{{ total }}</span> 条记录
    </span>
    <div class="flex items-center gap-1">
      <button class="page-btn" aria-label="上一页" :disabled="pageNum <= 1" @click="go(pageNum - 1)">
        <AppIcon name="chevron_left" class="!text-[16px]" />
      </button>
      <template v-for="(p, i) in pages" :key="i">
        <span v-if="p === '...'" class="px-1.5 font-mono text-xs text-ink-faint">…</span>
        <button
          v-else
          class="page-btn"
          :class="{ 'page-btn-on': p === pageNum }"
          :aria-current="p === pageNum ? 'page' : undefined"
          @click="go(p)"
        >
          {{ String(p).padStart(2, '0') }}
        </button>
      </template>
      <button class="page-btn" aria-label="下一页" :disabled="pageNum >= totalPages" @click="go(pageNum + 1)">
        <AppIcon name="chevron_right" class="!text-[16px]" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.page-btn {
  display: inline-flex;
  height: 1.75rem;
  min-width: 1.75rem;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  border: 1px solid transparent;
  border-radius: 8px;
  font-family: var(--font-mono);
  font-size: 12px;
  font-variant-numeric: tabular-nums;
  color: var(--color-ink-muted);
  transition:
    background-color 0.16s,
    border-color 0.16s,
    color 0.16s;
}
.page-btn:hover:not(:disabled):not(.page-btn-on) {
  border-color: var(--color-line);
  background-color: var(--glass-strong);
  color: var(--color-ink);
}
.page-btn:disabled {
  cursor: not-allowed;
  opacity: 0.35;
}
.page-btn-on {
  background-color: var(--color-ink);
  color: var(--color-page);
  font-weight: 500;
}
</style>
