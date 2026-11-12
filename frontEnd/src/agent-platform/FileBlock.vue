<script setup>
import { computed } from 'vue'
import Icon from './Icon.vue'
import { t } from './preferences'
import { previewKind } from './filePreview'
import { fileType } from './fileTypes'
const props = defineProps({ path: { type: String, required: true }, size: Number, modifiedAt: Number, downloadUrl: { type: String, required: true } })
const emit = defineEmits(['preview'])
const canPreview = computed(() => !!previewKind(props.path))
const name = computed(() => props.path.split('/').pop())
const type = computed(() => fileType(props.path))
const pad = n => String(n).padStart(2, '0')
const timeLabel = computed(() => {
  if (!Number.isFinite(props.modifiedAt)) return ''
  const date = new Date(props.modifiedAt * 1000)
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`
})
const action = computed(() => t(canPreview.value ? 'artifacts.preview' : 'artifacts.download'))
const sizeLabel = computed(() => {
  if (!Number.isFinite(props.size) || props.size < 0) return ''
  if (props.size < 1024) return `${props.size} B`
  if (props.size < 1024 * 1024) return `${(props.size / 1024).toFixed(1)} KB`
  return `${(props.size / 1024 / 1024).toFixed(1)} MB`
})
</script>

<template>
  <div class="file-block">
    <component :is="canPreview ? 'button' : 'a'" class="file-block-open" :title="`${name} · ${action}`" :type="canPreview ? 'button' : undefined" :href="canPreview ? undefined : downloadUrl" :download="canPreview ? undefined : ''" @click="canPreview && emit('preview', path)">
      <span class="file-block-icon"><Icon :name="type.icon" :size="15" :class="['file-icon', 'file-tone-' + type.tone]" /></span>
      <span class="file-block-text"><strong>{{ name }}</strong><small>{{ [timeLabel || action, sizeLabel].filter(Boolean).join(' · ') }}</small></span>
    </component>
    <a class="file-block-download" :href="downloadUrl" download :aria-label="t('Download')"><Icon name="Download" :size="14" /></a>
  </div>
</template>
