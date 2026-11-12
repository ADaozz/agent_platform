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
    <Transition name="modal">
      <div v-if="open" class="modal-scrim" @mousedown.self="emit('close')">
        <div class="modal-panel" role="dialog" aria-modal="true" :aria-label="title" :style="{ maxWidth: width || '480px' }">
          <div class="modal-head">
            <div class="min-w-0 flex-1">
              <h3 class="modal-title">{{ title }}</h3>
              <span class="tri-bar modal-tri" aria-hidden="true"></span>
            </div>
            <button class="modal-close" aria-label="关闭" @click="emit('close')">
              <AppIcon name="close" class="!text-[17px]" />
            </button>
          </div>
          <div class="px-6 py-5">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-scrim {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 10vh 1.5rem 1.5rem;
  background-color: var(--overlay);
  backdrop-filter: blur(6px) saturate(0.9);
}
.modal-panel {
  position: relative;
  width: 100%;
  border: 1px solid var(--color-line);
  border-radius: 16px;
  overflow: hidden;
  background-color: var(--color-card);
  box-shadow: var(--shadow-panel);
}
.modal-head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1.125rem 1rem 0.25rem 1.5rem;
}
.modal-tri {
  width: 72px;
  height: 3px;
  margin-top: 0.5rem;
}
.modal-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-ink);
}
.modal-close {
  display: flex;
  height: 1.75rem;
  width: 1.75rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-ink-muted);
  transition:
    background-color 0.16s,
    color 0.16s;
}
.modal-close:hover {
  background-color: var(--glass-strong);
  color: var(--color-ink);
}
.modal-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border-top: 1px solid var(--color-line);
  background-color: var(--glass);
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.18s var(--ease-out);
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 0.2s var(--ease-out);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: translateY(8px);
}
</style>
