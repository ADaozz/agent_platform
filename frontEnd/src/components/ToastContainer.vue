<script setup lang="ts">
import { toasts, type ToastType } from '@/composables/toast'
import AppIcon from '@/components/AppIcon.vue'
import type { IconName } from '@/icons'

const typeIcon: Record<ToastType, IconName> = {
  success: 'check_circle',
  error: 'error',
  info: 'info',
}
</script>

<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed top-4 left-1/2 z-[100] flex w-full max-w-md -translate-x-1/2 flex-col items-center gap-2 px-4">
      <TransitionGroup
        enter-active-class="transition duration-200"
        enter-from-class="opacity-0 -translate-y-2"
        leave-active-class="transition duration-200"
        leave-to-class="opacity-0"
      >
        <div v-for="t in toasts" :key="t.id" class="toast-card" :class="'toast-' + t.type" role="status">
          <span class="toast-code">
            <AppIcon :name="typeIcon[t.type]" class="!text-[17px]" />
          </span>
          <span class="min-w-0 flex-1">{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
/* 通报条：恒定碳黑的磨砂玻璃，状态由左侧色条与代号表达 */
.toast-card {
  pointer-events: auto;
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.875rem 0.625rem 0;
  border: 1px solid rgb(245 237 220 / 0.14);
  border-radius: 10px;
  background-color: rgb(26 26 24 / 0.86);
  backdrop-filter: blur(14px) saturate(1.2);
  box-shadow: 0 14px 40px -12px rgb(0 0 0 / 0.55);
  font-size: 13px;
  color: #f2ead9;
  --tone: var(--color-steel);
}
/* 成功提示：只留图标和文字，不加底板；文字随主题取色，保证在浅色页面上可读 */
.toast-success {
  --tone: var(--color-success);
  justify-content: center;
  padding-right: 0;
  border-color: transparent;
  background-color: transparent;
  backdrop-filter: none;
  box-shadow: none;
  color: var(--color-ink);
}
.toast-success .toast-code {
  padding-left: 0;
  border-left: 0;
}
.toast-success .flex-1 {
  flex: 0 1 auto;
}
.toast-error {
  --tone: #e2695f;
}
.toast-info {
  --tone: #9cb5c6;
}
.toast-code {
  display: inline-flex;
  flex-shrink: 0;
  align-items: center;
  gap: 6px;
  padding: 2px 0 2px 0.75rem;
  border-left: 3px solid var(--tone);
  font-family: var(--font-mono);
  font-size: 10.5px;
  letter-spacing: 0.12em;
  color: var(--tone);
}
</style>
