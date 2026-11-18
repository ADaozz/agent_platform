<script setup>
import { ref, computed, watch, onMounted, onUnmounted, nextTick, useId } from 'vue'
import Icon from './Icon.vue'
import { t } from './preferences'
import { vPopoverPlacement } from './popoverPlacement'
import { fileType } from './fileTypes'

const props = defineProps({ files: { type: Array, default: () => [] }, modelValue: String })
const emit = defineEmits(['update:modelValue'])
const root = ref(null), menu = ref(null), opened = ref(false), focused = ref(0)
const menuId = useId()
const current = computed(() => props.files.findIndex(file => file.path === props.modelValue))
function open() { focused.value = Math.max(0, current.value); opened.value = true }
function close() { opened.value = false }
function choose(index) {
  const file = props.files[index]
  if (!file) return
  close(); emit('update:modelValue', file.path)
}
function keydown(event) {
  if (event.key === 'Tab') { close(); return }
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End', 'Enter', ' ', 'Escape'].includes(event.key)) return
  event.preventDefault(); event.stopPropagation()
  if (event.key === 'Escape') { close(); return }
  if (event.key === 'Enter' || event.key === ' ') { opened.value ? choose(focused.value) : open(); return }
  if (!opened.value) {
    open()
    if (event.key === 'Home') focused.value = 0
    if (event.key === 'End') focused.value = props.files.length - 1
    return
  }
  const last = props.files.length - 1
  if (event.key === 'Home') focused.value = 0
  else if (event.key === 'End') focused.value = last
  else focused.value = (focused.value + (event.key === 'ArrowDown' ? 1 : -1) + props.files.length) % props.files.length
}
function outside(event) { if (!root.value?.contains(event.target)) close() }
watch(focused, async () => { await nextTick(); menu.value?.children[focused.value]?.scrollIntoView({ block: 'nearest' }) })
watch(opened, async value => { if (value) { await nextTick(); menu.value?.children[focused.value]?.scrollIntoView({ block: 'nearest' }) } })
watch(() => props.files.length, length => { if (!length) close(); focused.value = Math.min(focused.value, Math.max(0, length - 1)) })
onMounted(() => document.addEventListener('pointerdown', outside))
onUnmounted(() => document.removeEventListener('pointerdown', outside))
</script>

<template>
  <div ref="root" class="preview-file-select" :class="{ opened }">
    <button type="button" class="preview-file-trigger dropdown-trigger" role="combobox" :aria-label="t('artifacts.select')" aria-haspopup="listbox" :aria-expanded="opened" :aria-controls="opened ? menuId : undefined" :aria-activedescendant="opened ? `${menuId}-${focused}` : undefined" :disabled="!files.length" @click="opened ? close() : open()" @keydown="keydown">
      <span :title="modelValue">{{ modelValue || t('artifacts.select') }}</span><Icon name="ChevronDown" :size="14" class="dropdown-chevron" />
    </button>
    <div v-if="opened" :id="menuId" ref="menu" v-popover-placement class="popover preview-file-menu dropdown-surface" role="listbox" :aria-label="t('artifacts.select')">
      <button v-for="(file, index) in files" :id="`${menuId}-${index}`" :key="file.path" type="button" class="preview-file-option dropdown-item" :class="{ focused: focused === index }" role="option" :aria-selected="file.path === modelValue" tabindex="-1" @pointerenter="focused = index" @mousedown.prevent @click="choose(index)">
        <Icon :name="fileType(file.path).icon" :size="16" :class="['file-icon', 'file-tone-' + fileType(file.path).tone]" /><span class="dropdown-label" :title="file.path">{{ file.path }}</span><Icon v-if="file.path === modelValue" name="Check" class="dropdown-check" />
      </button>
    </div>
  </div>
</template>

<style scoped>
.preview-file-select{position:relative;flex:0 1 auto;min-width:0;max-width:260px}
.preview-file-select.opened{z-index:2}
.preview-file-trigger{display:flex;align-items:center;gap:8px;width:auto;max-width:100%;min-width:0;min-height:32px;padding:5px 8px;text-align:left;border-radius:6px;color:var(--text-primary);background:transparent;font-size:12px}
.preview-file-trigger:hover,.preview-file-select.opened .preview-file-trigger{background:var(--surface-hover)}
.preview-file-trigger>span{flex:1;min-width:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.preview-file-trigger:focus-visible{outline:2px solid var(--border-focus);outline-offset:2px}
.popover.preview-file-menu{width:max(100%, 240px);max-height:320px;z-index:50}
</style>
