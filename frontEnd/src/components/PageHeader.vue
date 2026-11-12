<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import type { IconName } from '@/icons'

const props = defineProps<{
  title: string
  desc?: string
  icon?: IconName
}>()

// 徽标图标默认取当前路由的 meta.icon，与侧栏菜单保持一致
const route = useRoute()
const emblem = computed(() => props.icon ?? (route.meta.icon as IconName | undefined))
</script>

<template>
  <!-- 功能卡片式标题栏（参考 LONETRAIL 功能卡片）：同心环徽标 + 标题 + 说明，底边信号橙结构线；右侧为操作位 -->
  <header class="page-head">
    <div v-if="emblem" class="page-head-emblem" aria-hidden="true">
      <span class="page-head-rings"></span>
      <span class="page-head-disc"><AppIcon :name="emblem" /></span>
    </div>
    <div class="page-head-text">
      <h1 class="page-head-title">{{ title }}</h1>
      <p v-if="desc || $slots.desc" class="page-head-desc">
        <slot name="desc">{{ desc }}</slot>
      </p>
    </div>
    <div v-if="$slots.default" class="page-head-actions">
      <slot />
    </div>
    <span class="page-head-strip" aria-hidden="true"></span>
  </header>
</template>

<style scoped>
.page-head {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.75rem 1.25rem;
  overflow: hidden;
  padding: 1.125rem 1.5rem 1.375rem 1.375rem;
  border: 1px solid var(--color-line);
  border-radius: 14px;
  background-color: var(--color-card);
}
.page-head-emblem {
  position: relative;
  display: flex;
  height: 3rem;
  width: 3rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
}
/* 同心环：从徽标向外扩散并渐隐，被卡片边缘裁切 */
.page-head-rings {
  position: absolute;
  top: 50%;
  left: 50%;
  height: 15rem;
  width: 15rem;
  transform: translate(-50%, -50%);
  border-radius: 50%;
  background: repeating-radial-gradient(circle, transparent 0 13px, var(--glass-edge) 13px 14px);
  -webkit-mask-image: radial-gradient(circle, #000 18%, transparent 68%);
  mask-image: radial-gradient(circle, #000 18%, transparent 68%);
  pointer-events: none;
}
.page-head-disc {
  position: relative;
  display: flex;
  height: 3rem;
  width: 3rem;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: var(--color-signal);
  color: var(--on-signal);
}
.page-head-disc .app-icon {
  font-size: 24px;
}
.page-head-text {
  position: relative;
  min-width: 0;
  flex: 1 1 16rem;
}
.page-head-title {
  font-size: 24px;
  line-height: 1.2;
  font-weight: 800;
  letter-spacing: 0.01em;
  color: var(--color-ink);
}
.page-head-desc {
  margin-top: 0.375rem;
  max-width: 68ch;
  font-size: 13px;
  line-height: 1.6;
  color: var(--color-ink-muted);
}
.page-head-actions {
  position: relative;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 0.5rem;
}
.page-head-strip {
  position: absolute;
  inset: auto 0 0 0;
  height: 4px;
  background: var(--color-signal);
}
</style>
