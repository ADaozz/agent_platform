<script setup>
import { computed, nextTick, ref, useId } from 'vue'
import Icon from './Icon.vue'
import ProviderIcon from '@/components/ProviderIcon.vue'
import { MODEL_PRESETS } from '@/utils/modelPresets'
import { sortReasoningEfforts } from '@/utils/reasoningEfforts'
import { t } from './preferences'
import { vPopoverPlacement } from './popoverPlacement'

const props = defineProps({
  profiles: { type: Array, required: true },
  modelId: { type: String, required: true },
  effort: { type: String, required: true },
})
const emit = defineEmits(['select', 'close'])
const root = ref(null)
const search = ref('')
const moreOpen = ref(false)
const reasoningId = ref('')
const moreId = useId()

const groups = computed(() => {
  const providers = new Map()
  for (const model of props.profiles) {
    const id = model.id.split('/')[0] || model.id
    if (!providers.has(id)) {
      providers.set(id, { id, label: MODEL_PRESETS.find(preset => preset.id === id)?.label || id, models: [] })
    }
    providers.get(id).models.push(model)
  }
  return [...providers.values()]
})
const currentGroup = computed(() => groups.value.find(group => group.models.some(model => model.id === props.modelId)) ?? groups.value[0])
const otherGroups = computed(() => groups.value.filter(group => group !== currentGroup.value))
const query = computed(() => search.value.trim().toLowerCase())
const primaryGroups = computed(() => {
  if (!query.value) return currentGroup.value ? [currentGroup.value] : []
  return groups.value.map(group => ({
    ...group,
    models: group.models.filter(model => [model.id, model.model, t(group.label)].some(label => label.toLowerCase().includes(query.value))),
  })).filter(group => group.models.length)
})
const showMore = computed(() => moreOpen.value && !query.value && otherGroups.value.length > 0)
const panels = computed(() => [
  { key: 'primary', groups: primaryGroups.value },
  ...(showMore.value ? [{ key: 'secondary', groups: otherGroups.value }] : []),
])
const reasoning = computed(() => props.profiles.find(model => model.id === reasoningId.value))
const reasoningChoice = computed(() => reasoningId.value === props.modelId ? props.effort : reasoning.value?.default_reasoning_effort || '')

async function focusItem(selector) {
  await nextTick()
  root.value?.querySelector(selector)?.focus()
}
function openMore(focus = false) {
  moreOpen.value = true
  if (focus) focusItem('.model-picker-secondary .model-picker-option')
}
function hoverMore(event) {
  if (event.pointerType === 'mouse' && window.matchMedia('(min-width: 601px)').matches) openMore()
}
function closeMore() {
  moreOpen.value = false
  focusItem('.model-picker-more')
}
function editEffort(model) {
  reasoningId.value = model.id
  focusItem('.model-picker-reasoning .model-picker-back')
}
function backToModels() {
  const id = reasoningId.value
  reasoningId.value = ''
  focusItem(`[data-model-edit="${CSS.escape(id)}"]`)
}
function escape() {
  if (reasoning.value) backToModels()
  else if (showMore.value) closeMore()
  else emit('close')
}
</script>

<template>
  <div ref="root" v-popover-placement="'.chat-page'" class="popover model-picker" :class="{ 'model-picker-expanded': !reasoning && showMore }" @click.stop @keydown.esc.stop.prevent="escape">
    <div v-if="reasoning" class="model-picker-panel model-picker-reasoning">
      <div class="model-picker-card dropdown-surface composer-menu-card">
        <button type="button" class="dropdown-item model-picker-back" @click="backToModels">
          <Icon name="ArrowLeft" :size="14" /><span class="dropdown-label">{{ t('model.back') }}</span>
        </button>
        <div class="model-picker-effort-heading">
          <strong>{{ t('Reasoning effort') }}</strong>
          <small>{{ reasoning.model }}</small>
        </div>
        <div class="model-picker-options" role="group" :aria-label="t('Reasoning effort')">
          <button v-for="strength in ['', ...sortReasoningEfforts(reasoning.reasoning_efforts)]" :key="strength" type="button" class="dropdown-item" :aria-pressed="reasoningChoice === strength" @click="emit('select', reasoning.id, strength)">
            <span class="dropdown-label">{{ strength || t('Default') }}</span>
            <Icon v-if="reasoningChoice === strength" name="Check" class="dropdown-check" />
          </button>
        </div>
      </div>
    </div>
    <template v-else>
      <div v-for="panel in panels" :key="panel.key" class="model-picker-panel" :class="'model-picker-' + panel.key">
        <div :id="panel.key === 'secondary' ? moreId : undefined" class="model-picker-card dropdown-surface composer-menu-card" :aria-label="panel.key === 'secondary' ? t('model.more') : undefined" role="group" @keydown.left="panel.key === 'secondary' && closeMore()">
          <template v-if="panel.key === 'primary'">
            <label v-if="groups.length" class="model-picker-search">
              <Icon name="Search" :size="15" />
              <input v-model="search" type="search" :aria-label="t('model.search')" :placeholder="t('model.search')" @focus="moreOpen = false" @input="moreOpen = false">
            </label>
            <button
              v-if="otherGroups.length && !query"
              type="button"
              class="dropdown-item model-picker-more"
              :aria-expanded="showMore"
              :aria-controls="showMore ? moreId : undefined"
              @pointerenter="hoverMore"
              @click="openMore(true)"
              @keydown.right.prevent="openMore(true)"
            >
              <Icon name="Layers" :size="15" /><span class="dropdown-label">{{ t('model.more') }}</span><Icon name="ChevronRight" class="dropdown-branch-arrow" />
            </button>
          </template>
          <button v-else type="button" class="dropdown-item model-picker-back model-picker-mobile-back" @click="closeMore">
            <Icon name="ArrowLeft" :size="14" /><span class="dropdown-label">{{ t('model.back') }}</span>
          </button>
          <div class="model-picker-options">
            <p v-if="!groups.length" class="popover-empty">{{ t('Add a model provider to start.') }}</p>
            <p v-else-if="!panel.groups.length" class="popover-empty">{{ t('model.noMatches') }}</p>
            <div v-for="group in panel.groups" :key="group.id" role="group" :aria-label="t(group.label)" class="model-picker-group">
              <div class="dropdown-heading">{{ t(group.label) }}</div>
              <div v-for="model in group.models" :key="model.id" class="model-picker-row" :data-selected="modelId === model.id">
                <button type="button" class="dropdown-item model-picker-option" :aria-pressed="modelId === model.id" @click="emit('select', model.id, modelId === model.id ? effort : undefined)">
                  <ProviderIcon :provider="group.id" :size="16" />
                  <span class="dropdown-label" :title="model.model">{{ model.model }}</span>
                  <span v-if="!model.configured" class="unconfigured">{{ t('未就绪') }}</span>
                  <Icon v-if="modelId === model.id" name="Check" class="dropdown-check" />
                </button>
                <button
                  v-if="model.reasoning_efforts.length"
                  type="button"
                  class="model-picker-edit"
                  :data-model-edit="model.id"
                  :aria-label="t('model.editEffort', { name: model.model })"
                  :title="t('Reasoning effort')"
                  @click="editEffort(model)"
                ><Icon name="Pencil" :size="13" /></button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.popover.model-picker {
  display: flex;
  width: max-content;
  max-width: calc(100vw - 24px);
  max-height: min(350px, 68dvh);
  gap: 7px;
  overflow: visible;
}
.model-picker-panel {
  display: flex;
  flex-direction: column;
  width: 250px;
  min-width: 0;
  min-height: 0;
}
.model-picker-secondary {
  width: 238px;
  padding-top: 43px;
}
.model-picker-card {
  display: flex;
  flex-direction: column;
  min-height: 0;
}
.model-picker-card > :not(.model-picker-options) {
  flex-shrink: 0;
}
.model-picker-search {
  display: flex;
  align-items: center;
  gap: 7px;
  min-height: 33px;
  margin: 0 3px 4px;
  padding-inline: 5px;
  border-bottom: 1px solid var(--dropdown-divider);
  color: var(--text-muted);
}
.model-picker-search:focus-within {
  border-color: var(--signal-text);
  color: var(--signal-text);
}
.model-picker .model-picker-search input {
  width: 100%;
  min-width: 0;
  padding: 4px 0;
  border: 0;
  background: transparent;
  box-shadow: none;
  color: var(--text-primary);
  font-size: 12px;
}
.model-picker-search input::placeholder {
  color: var(--text-muted);
}
.model-picker-options {
  min-height: 0;
  overflow: auto;
  overscroll-behavior: contain;
  scrollbar-width: thin;
}
.model-picker-group + .model-picker-group {
  margin-top: 4px;
  border-top: 1px solid var(--dropdown-divider);
}
.model-picker-group .dropdown-heading {
  padding-block: 4px 2px;
}
.model-picker-row {
  display: flex;
  align-items: center;
  border-radius: var(--dropdown-row-radius);
}
.model-picker-card .model-picker-option {
  flex: 1;
  min-width: 0;
}
.model-picker-card .model-picker-more[aria-expanded='true'] {
  background: var(--dropdown-hover);
}
.model-picker-row[data-selected='true'] {
  background: var(--composer-menu-selected);
}
.model-picker-card .model-picker-edit {
  display: grid;
  width: 26px;
  height: 25px;
  flex-shrink: 0;
  place-items: center;
  margin-inline-end: 2px;
  border-radius: var(--dropdown-row-radius);
  color: var(--text-muted);
}
.model-picker-card .model-picker-edit:hover,
.model-picker-card .model-picker-edit:focus-visible {
  background: var(--dropdown-hover);
  color: var(--text-primary);
}
.model-picker-reasoning .model-picker-effort-heading {
  margin-bottom: 3px;
  padding: 5px 8px 7px;
  border-block-end: 1px solid var(--dropdown-divider);
  font-size: 12px;
}
.model-picker-effort-heading small {
  display: block;
  color: var(--text-muted);
  overflow-wrap: anywhere;
}
.model-picker-card .model-picker-mobile-back {
  display: none;
}
@media (max-width: 600px) {
  .model-picker-expanded .model-picker-primary {
    display: none;
  }
  .model-picker-secondary {
    width: 250px;
    padding-top: 0;
  }
  .model-picker-card .model-picker-mobile-back {
    display: flex;
    margin-bottom: 3px;
    border-block-end: 1px solid var(--dropdown-divider);
  }
}
@media (pointer: coarse) {
  .model-picker-card .model-picker-edit { width: 32px; height: 32px; }
}
</style>
