<script setup lang="ts">
import AppIcon from '@/components/AppIcon.vue'

defineProps<{
  open: boolean
  title: string
  width?: string
}>()

const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-150"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-150"
      leave-to-class="opacity-0"
    >
      <div
        v-if="open"
        class="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/40 p-6 pt-[10vh]"
        @mousedown.self="emit('close')"
      >
        <div
          class="w-full rounded-[10px] border border-line bg-white shadow-2xl"
          :style="{ maxWidth: width || '480px' }"
        >
          <div class="flex items-center justify-between border-b border-line px-6 py-4">
            <h3 class="text-base font-semibold text-ink">{{ title }}</h3>
            <button
              class="flex h-7 w-7 items-center justify-center rounded text-ink-muted transition-colors hover:bg-gray-100 hover:text-ink"
              @click="emit('close')"
            >
              <AppIcon name="close" />
            </button>
          </div>
          <div class="px-6 py-5">
            <slot />
          </div>
          <div v-if="$slots.footer" class="flex items-center justify-end gap-2 border-t border-line px-6 py-4">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>
