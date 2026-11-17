<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, useId } from 'vue'
import AppIcon from '@/components/AppIcon.vue'
import ProviderIcon from '@/components/ProviderIcon.vue'
import { tr } from '@/composables/preferences'

const props = defineProps<{
  providers: Array<{ id: string; label: string }>
  models: Array<{ provider: string; id: string }>
  provider: string
  model: string
}>()
const emit = defineEmits<{ select: [provider: string, model: string] }>()
const trigger = ref<HTMLButtonElement>()
const popup = ref<HTMLElement>()
const primary = ref<HTMLElement>()
const secondary = ref<HTMLElement>()
const open = ref(false)
const activeProvider = ref('')
const position = ref<Record<string, string>>({})
const id = useId()
const label = computed(() => props.model || props.providers.find(item => item.id === props.provider)?.label || tr('全部服务商'))
const models = computed(() => [...new Set(props.models.filter(item => item.provider === activeProvider.value).map(item => item.id))])
const activeLabel = computed(() => props.providers.find(item => item.id === activeProvider.value)?.label ?? '')
function items(menu?: HTMLElement) { return [...(menu?.querySelectorAll<HTMLButtonElement>('[role^="menuitem"]') ?? [])] }
async function show() {
  if (open.value) { close(); return }
  activeProvider.value = props.provider || props.providers[0]?.id || ''
  const rect = trigger.value!.getBoundingClientRect()
  const width = Math.min(500, window.innerWidth - 24)
  const below = window.innerHeight - rect.bottom - 18
  const above = rect.top - 18
  const upward = below < 200 && above > below
  position.value = {
    width: `${width}px`, left: `${Math.max(12, Math.min(rect.left, window.innerWidth - width - 12))}px`,
    ...(upward ? { bottom: `${window.innerHeight - rect.top + 6}px` } : { top: `${rect.bottom + 6}px` }),
    maxHeight: `${Math.max(80, Math.min(360, upward ? above : below))}px`,
  }
  open.value = true
  await nextTick()
  const target = items(primary.value).find(item => item.dataset.provider === props.provider) ?? items(primary.value)[0]
  target?.focus()
}
function close(restore = true) { open.value = false; if (restore) trigger.value?.focus() }
function select(provider: string, model = '') { emit('select', provider, model); close() }
function outside(event: Event) {
  const node = event.target as Node
  if (open.value && !popup.value?.contains(node) && !trigger.value?.contains(node)) close(false)
}
function scrolled(event: Event) { if (open.value && (!(event.target instanceof Node) || !popup.value?.contains(event.target))) close(false) }
function resized() { if (open.value) close(false) }
async function keydown(event: KeyboardEvent) {
  if (!open.value) return
  if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); close(); return }
  if (event.key === 'Tab') { close(); return }
  const target = event.target as HTMLElement
  const inSecondary = !!secondary.value?.contains(target)
  if (event.key === 'ArrowRight' && !inSecondary && activeProvider.value) {
    event.preventDefault(); await nextTick(); items(secondary.value)[0]?.focus(); return
  }
  if (event.key === 'ArrowLeft' && inSecondary) {
    event.preventDefault(); items(primary.value).find(item => item.dataset.provider === activeProvider.value)?.focus(); return
  }
  if (!['ArrowDown', 'ArrowUp', 'Home', 'End'].includes(event.key)) return
  event.preventDefault()
  const buttons = items(inSecondary ? secondary.value : primary.value)
  const index = buttons.indexOf(target as HTMLButtonElement)
  const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (event.key === 'ArrowDown' ? 1 : -1) + buttons.length) % buttons.length
  buttons[next]?.focus()
}
onMounted(() => {
  document.addEventListener('pointerdown', outside, true)
  window.addEventListener('scroll', scrolled, true)
  window.addEventListener('resize', resized)
})
onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', outside, true)
  window.removeEventListener('scroll', scrolled, true)
  window.removeEventListener('resize', resized)
})
</script>

<template>
  <div class="usage-model-filter">
    <button ref="trigger" type="button" class="filter-trigger" aria-haspopup="menu" :aria-expanded="open" :aria-controls="id" :aria-label="tr('筛选服务商和模型')" :title="label" @click="show" @keydown.down.prevent="show" @keydown.up.prevent="show">
      <ProviderIcon v-if="provider" :provider="provider" :size="18" /><span>{{ label }}</span><AppIcon name="expand_more" />
    </button>
    <Teleport to="body">
      <div v-if="open" :id="id" ref="popup" class="usage-filter-popup" :style="position" @keydown="keydown">
        <div ref="primary" class="provider-menu" role="menu" :aria-label="tr('服务商')">
          <button role="menuitemradio" tabindex="-1" :aria-checked="!provider" data-provider="" @click="select('')">{{ tr('全部服务商') }}<AppIcon v-if="!provider" name="check_circle" /></button>
          <button v-for="item in providers" :key="item.id" role="menuitem" tabindex="-1" aria-haspopup="menu" :aria-expanded="activeProvider === item.id" :aria-controls="`${id}-models`" :data-provider="item.id" :class="{ active: activeProvider === item.id }" @mouseenter="activeProvider = item.id" @focus="activeProvider = item.id" @click="activeProvider = item.id">
            <ProviderIcon :provider="item.id" :size="20" /><span>{{ item.label }}</span><AppIcon name="chevron_right" />
          </button>
        </div>
        <div v-if="activeProvider" :id="`${id}-models`" ref="secondary" class="model-menu" role="menu" :aria-label="activeLabel">
          <button role="menuitemradio" tabindex="-1" :aria-checked="provider === activeProvider && !model" @click="select(activeProvider)">{{ tr('全部模型') }}<AppIcon v-if="provider === activeProvider && !model" name="check_circle" /></button>
          <button v-for="item in models" :key="item" role="menuitemradio" tabindex="-1" :aria-checked="provider === activeProvider && model === item" @click="select(activeProvider, item)"><span>{{ item }}</span><AppIcon v-if="provider === activeProvider && model === item" name="check_circle" /></button>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.usage-model-filter { min-width: 0; width: 100%; max-width: 100%; }
.filter-trigger { display: flex; align-items: center; gap: 8px; width: 100%; height: 36px; padding: 0 10px; border: 1px solid var(--color-line); border-radius: 8px; background: var(--field); color: var(--color-ink); font-size: 13px; text-align: left; }
.filter-trigger > span:not(.provider-avatar) { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.filter-trigger > .app-icon { flex-shrink: 0; color: var(--color-ink-muted); }
.usage-filter-popup { position: fixed; z-index: 80; display: flex; overflow: hidden; border: 1px solid var(--color-line); border-radius: 8px; background: var(--color-card); box-shadow: var(--shadow-panel); color: var(--color-ink); }
.provider-menu { flex: 0 0 165px; }
.model-menu { flex: 1; min-width: 0; border-left: 1px solid var(--color-line); }
.provider-menu, .model-menu { overflow-y: auto; padding: 4px; }
.usage-filter-popup button { display: flex; align-items: center; gap: 8px; width: 100%; min-height: 36px; padding: 8px; border-radius: 4px; color: var(--color-ink-secondary); font-size: 12px; text-align: left; }
.usage-filter-popup button > span:not(.provider-avatar) { flex: 1; min-width: 0; overflow-wrap: anywhere; }
.usage-filter-popup button > .app-icon:last-child { margin-left: auto; flex-shrink: 0; font-size: 14px; }
.usage-filter-popup button:is(:hover, :focus-visible, .active) { background: var(--color-hover); color: var(--color-ink); }
.usage-filter-popup button[aria-checked='true'] { color: var(--color-primary); }
button:focus-visible { outline: 2px solid var(--color-primary); outline-offset: -2px; }
@media (max-width: 600px) { .provider-menu { flex-basis: 135px; } }
</style>
