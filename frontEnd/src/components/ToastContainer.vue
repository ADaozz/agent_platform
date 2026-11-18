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
    <div class="pointer-events-none fixed top-16 left-1/2 z-[100] flex w-full max-w-md -translate-x-1/2 flex-col items-center gap-2 px-4">
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
/* 通报条：磨砂底板 + 左侧色条；成功/错误用状态色浅底，避免在深色登录页上融掉 */
.toast-card {
  pointer-events: auto;
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.75rem;
  padding: 0.625rem 0.875rem 0.625rem 0;
  border: 1px solid color-mix(in srgb, var(--tone) 35%, var(--color-line));
  border-radius: 10px;
  background-color: color-mix(in srgb, var(--tone) 14%, var(--color-card));
  backdrop-filter: blur(14px) saturate(1.2);
  box-shadow: 0 14px 40px -12px rgb(0 0 0 / 0.35);
  font-size: 13px;
  color: var(--color-ink);
  --tone: var(--color-steel);
}
.toast-success {
  --tone: var(--color-success);
}
.toast-error {
  --tone: var(--color-danger);
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
