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
  <!-- 状态牌：色块 + 标签 -->
  <span class="status-tag" :class="tag.cls">
    <span v-if="dot !== false" class="status-tag-lamp"></span>
    {{ tag.label }}
  </span>
</template>

<style scoped>
/* 状态牌：不做底色胶囊，只用一枚 2px 色块 + 状态色文字，与三色标识同一套语言 */
.status-tag {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  background-color: transparent !important;
  font-size: 12px;
  font-weight: 600;
  line-height: 16px;
  letter-spacing: 0.06em;
  white-space: nowrap;
}
.status-tag-lamp {
  width: 2px;
  height: 11px;
  flex-shrink: 0;
  background-color: currentColor;
}
</style>
