<script setup lang="ts">
import { computed } from 'vue'
import ConfirmModal from '@/components/ConfirmModal.vue'
import { tr } from '@/composables/preferences'
// @ts-ignore: shared with the JavaScript workspace UI
import { answerDelete, deleteRequest, sessionTitle } from '@/agent-platform/workspace'
// @ts-ignore: shared with the JavaScript workspace UI
import { t } from '@/agent-platform/preferences'

const message = computed(() =>
  deleteRequest.value
    ? t('确定删除对话「{title}」？删除后无法恢复。', { title: sessionTitle(deleteRequest.value.session) })
    : '',
)
</script>

<template>
  <ConfirmModal
    :open="!!deleteRequest"
    :title="tr('删除对话')"
    :message="message"
    danger
    @close="answerDelete(false)"
    @confirm="answerDelete(true)"
  />
</template>
