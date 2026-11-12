<script setup lang="ts">
defineProps<{
  open: boolean
  width?: string
}>()

const emit = defineEmits<{ close: [] }>()
</script>

<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition duration-200"
      enter-from-class="opacity-0"
      leave-active-class="transition duration-200"
      leave-to-class="opacity-0"
    >
      <div v-if="open" class="drawer-scrim" @click="emit('close')"></div>
    </Transition>
    <Transition
      enter-active-class="transition-transform duration-250"
      enter-from-class="translate-x-full"
      leave-active-class="transition-transform duration-250"
      leave-to-class="translate-x-full"
    >
      <aside v-if="open" class="drawer-panel" :style="{ width: width || '440px', maxWidth: '90vw' }">
        <span class="drawer-tri" aria-hidden="true"></span>
        <slot />
      </aside>
    </Transition>
  </Teleport>
</template>

<style scoped>
.drawer-scrim {
  position: fixed;
  inset: 0;
  z-index: 40;
  background-color: var(--overlay);
  backdrop-filter: blur(4px);
}
.drawer-panel {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  z-index: 50;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-left: 1px solid var(--color-line);
  border-radius: 18px 0 0 18px;
  background-color: var(--color-card);
  box-shadow: var(--shadow-panel);
}
.drawer-tri {
  flex-shrink: 0;
  height: 4px;
  background: var(--tricolor-h);
}
</style>
