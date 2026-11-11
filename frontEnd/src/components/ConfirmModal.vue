<script setup lang="ts">
import BaseModal from './BaseModal.vue'
import { tr } from '@/composables/preferences'

defineProps<{
  open: boolean
  title?: string
  message: string
  loading?: boolean
  danger?: boolean
}>()

const emit = defineEmits<{ close: []; confirm: [] }>()
</script>

<template>
  <BaseModal :open="open" :title="title || tr('确认操作')" width="400px" @close="emit('close')">
    <p class="text-sm text-ink-secondary">{{ message }}</p>
    <template #footer>
      <button class="btn-ghost" @click="emit('close')">{{ tr('取消') }}</button>
      <button
        :class="danger ? 'btn-danger' : 'btn-primary'"
        :disabled="loading"
        @click="emit('confirm')"
      >
        {{ loading ? tr('处理中…') : tr('确定') }}
      </button>
    </template>
  </BaseModal>
</template>
