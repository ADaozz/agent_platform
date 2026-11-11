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
      <div v-if="open" class="fixed inset-0 z-40 bg-black/30" @click="emit('close')"></div>
    </Transition>
    <Transition
      enter-active-class="transition-transform duration-250"
      enter-from-class="translate-x-full"
      leave-active-class="transition-transform duration-250"
      leave-to-class="translate-x-full"
    >
      <aside
        v-if="open"
        class="fixed inset-y-0 right-0 z-50 flex flex-col border-l border-line bg-white shadow-2xl"
        :style="{ width: width || '440px', maxWidth: '90vw' }"
      >
        <slot />
      </aside>
    </Transition>
  </Teleport>
</template>
