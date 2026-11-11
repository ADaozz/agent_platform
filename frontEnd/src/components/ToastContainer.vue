<script setup lang="ts">
import { toasts, type ToastType } from '@/composables/toast'
import AppIcon from '@/components/AppIcon.vue'
import type { IconName } from '@/icons'

const typeCls = {
  success: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  error: 'border-red-200 bg-red-50 text-red-800',
  info: 'border-blue-200 bg-blue-50 text-blue-800',
}

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
        <div
          v-for="t in toasts"
          :key="t.id"
          class="pointer-events-auto flex w-full items-center gap-2 rounded-md border px-4 py-2.5 text-sm shadow-lg"
          :class="typeCls[t.type]"
        >
          <AppIcon :name="typeIcon[t.type]" class="!text-[18px]" />
          <span>{{ t.message }}</span>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>
