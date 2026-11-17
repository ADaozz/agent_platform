<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import ProviderIcon from '@/components/ProviderIcon.vue'
import ModelRegistry from '@/components/ModelRegistry.vue'
import PageHeader from '@/components/PageHeader.vue'
import AppIcon from '@/components/AppIcon.vue'
import ModelSourceEditor from '@/components/ModelSourceEditor.vue'
import BaseModal from '@/components/BaseModal.vue'
import { tr } from '@/composables/preferences'
import { useAuthStore } from '@/stores/auth'
import { toast } from '@/composables/toast'
import { getGlobalModels, getPersonalModels, getModelOptions, saveGlobalModels, savePersonalModels, type LlmConfig, type ModelConfigResult, type ModelProfile } from '@/api/agentRuntime'
import { emptySource, modelIds, toForm, isPresetSourceName, type SourceForm } from '@/utils/modelConfigForm'
import { MODEL_PRESETS, applyPreset, type ModelPreset } from '@/utils/modelPresets'
import { cloneConfig, mergeModelSource, modelSettingsError, type ModelScope } from '@/utils/modelSettings'

interface Editor {
  id: string
  source: SourceForm
  scope: ModelScope | null
  target: ModelScope
  error: string
}
const auth = useAuthStore()
const isAdmin = computed(() => auth.isAdmin)
const scopes = computed<ModelScope[]>(() => isAdmin.value ? ['personal', 'global'] : ['personal'])
const scopeLabel = (scope: ModelScope) => tr(scope === 'personal' ? '我的模型' : '全局模型')
const providerLabel = (preset: ModelPreset) => preset.id === 'deepseek' ? preset.label : tr(preset.label)
const saved = reactive<Record<ModelScope, ModelConfigResult>>({
  personal: { llm: {}, revision: 0, profiles: [] }, global: { llm: {}, revision: 0, profiles: [] },
})
const dialogOpen = ref(false)
const dialogStep = ref<'choose' | 'configure' | 'defaults'>('choose')
const selectedEditorId = ref('')
const loading = ref(true), busy = ref(false), loadError = ref('')
const platformModels = ref<ModelProfile[]>([])
const editors = reactive<Record<string, Editor>>({})
const selectedEditor = computed(() => editors[selectedEditorId.value])
const selectedPreset = computed(() => MODEL_PRESETS.find(preset => preset.id === selectedEditor.value?.source.name && !selectedEditor.value?.id.startsWith('custom-new-')))
const settings = reactive<Record<ModelScope, { defaultModel: string; timeout: number | null; error: string }>>({
  personal: { defaultModel: '', timeout: null, error: '' }, global: { defaultModel: '', timeout: null, error: '' },
})
let serial = 0
const pending = ref<{ editor?: Editor; scope: ModelScope; settings?: boolean } | null>(null)
const confirmMessage = computed(() => tr('确认保存全局配置「{name}」？此变更将影响平台所有用户。', {
  name: pending.value?.settings ? tr('默认模型与请求设置') : pending.value?.editor?.source.name ?? '',
}))
const configured = (name: string, scope: ModelScope) => Boolean(saved[scope].llm.models?.[name])
function availableScopes(editor: Editor) {
  return scopes.value.filter(scope => !configured(editor.source.name.trim(), scope))
}
function newOfficial(preset: ModelPreset): SourceForm {
  const form = toForm({})
  return applyPreset(form, preset.id)
}
function openEditor(name: string, scope: ModelScope | null, preset?: ModelPreset) {
  const id = `${name}:${scope ?? 'new'}`
  if (!editors[id]) {
    const source = scope ? toForm(saved[scope].llm).sources.find(source => source.name === name) : preset ? newOfficial(preset) : emptySource()
    if (!source) return
    editors[id] = { id, source: cloneConfig(source), scope, target: scope ?? (scopes.value.find(s => !configured(name, s)) ?? 'personal'), error: '' }
  }
  selectedEditorId.value = id
  dialogStep.value = 'configure'
  dialogOpen.value = true
}
function addModel() { dialogStep.value = 'choose'; dialogOpen.value = true }
function addPreset(preset: ModelPreset) {
  if (scopes.value.some(scope => !configured(preset.id, scope))) openEditor(preset.id, null, preset)
}
function addCustom() {
  let editor = Object.values(editors).find(editor => editor.id.startsWith('custom-new-') && editor.scope === null)
  if (!editor) {
    const id = `custom-new-${++serial}`
    editor = { id, source: emptySource(), scope: null, target: 'personal', error: '' }
    editors[id] = editor
  }
  selectedEditorId.value = editor.id
  dialogStep.value = 'configure'
  dialogOpen.value = true
}
function editModel(provider: string, scope: ModelScope) {
  openEditor(provider, scope, MODEL_PRESETS.find(item => item.id === provider))
}
function closeDialog() {
  if (busy.value) return
  if (pending.value) pending.value = null
  else dialogOpen.value = false
}
const registryRows = computed(() => {
  const rows = scopes.value.flatMap(scope => toForm(saved[scope].llm).sources.flatMap(source => source.models.map(model => ({
    id: `${scope}:${source.name}/${model.key}`, provider: source.name, model: model.key, scope,
  }))))
  if (!isAdmin.value) rows.push(...platformModels.value.map(model => ({
    id: `global:${model.id}`, provider: model.id.split('/')[0] ?? '', model: model.model, scope: 'global' as const,
  })))
  return rows
})
function modelOptions(scope: ModelScope) { return modelIds(toForm(saved[scope].llm)) }
async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [mine, options, shared] = await Promise.all([getPersonalModels(), getModelOptions(), isAdmin.value ? getGlobalModels() : Promise.resolve(null)])
    saved.personal = mine
    if (shared) saved.global = shared
    platformModels.value = options.profiles.filter(p => p.scope === 'global')
    for (const scope of scopes.value) {
      settings[scope] = { defaultModel: saved[scope].llm.default ?? '', timeout: saved[scope].llm.timeout ?? null, error: '' }
    }
  } catch (e) { loadError.value = e instanceof Error ? e.message : String(e) }
  finally { loading.value = false }
}
function checkEditor(editor: Editor) {
  const target = editor.scope ?? editor.target
  if (target === 'global' && !isAdmin.value) throw new Error('仅管理员可以修改全局配置')
  if (editor.scope === null && configured(editor.source.name.trim(), target)) throw new Error('此范围已有该来源，请使用编辑入口')
  if (editor.scope === null && isPresetSourceName(editor.source.name) && editor.id.startsWith('custom-new-')) throw new Error('自定义来源不能使用官方供应商名称')
  // Empty official slots must not silently serialize into an undefined source.
  if (!editor.source.apiKey.trim() && !editor.source.savedKeyAt) throw new Error('请填写 API Key')
  return mergeModelSource(saved[target].llm, editor.source, target)
}
function requestSave(editor: Editor) {
  editor.error = ''
  try {
    checkEditor(editor)
    const scope = editor.scope ?? editor.target
    if (scope === 'global') pending.value = { editor, scope }
    else void persist({ editor, scope })
  } catch (e) { editor.error = e instanceof Error ? e.message : String(e) }
}
function requestSettings(scope: ModelScope) {
  settings[scope].error = ''
  if (scope === 'global') pending.value = { scope, settings: true }
  else void persist({ scope, settings: true })
}
async function persist(action: { editor?: Editor; scope: ModelScope; settings?: boolean }) {
  if (busy.value) return
  const { editor, scope } = action
  busy.value = true
  try {
    const llm: LlmConfig = editor ? checkEditor(editor) : cloneConfig(saved[scope].llm)
    if (action.settings) {
      const options = modelOptions(scope)
      if (options.length && !options.includes(settings[scope].defaultModel)) throw new Error('请选择默认模型')
      llm.default = settings[scope].defaultModel
      if (scope === 'global') {
        const timeout = settings[scope].timeout == null || String(settings[scope].timeout) === '' ? null : Number(settings[scope].timeout)
        if (timeout != null && (!Number.isFinite(timeout) || timeout < 1)) throw new Error('请求超时必须大于零')
        if (timeout != null) llm.timeout = timeout
        else delete llm.timeout
      }
    }
    const result = await (scope === 'personal' ? savePersonalModels : saveGlobalModels)(llm, saved[scope].revision)
    const previousDefault = saved[scope].llm.default ?? ''
    saved[scope] = result
    if (action.settings || settings[scope].defaultModel === previousDefault) settings[scope].defaultModel = result.llm.default ?? ''
    if (editor) {
      const name = editor.source.name.trim()
      const source = toForm(result.llm).sources.find(s => s.name === name)!
      const id = `${name}:${scope}`
      delete editors[editor.id]
      editors[id] = { id, source, scope, target: scope, error: '' }
      selectedEditorId.value = id
    }
    pending.value = null
    dialogOpen.value = false
    toast(tr('模型配置已保存'), 'success')
    // Options are display-only; failure must not turn a successful save into a retry.
    try { platformModels.value = (await getModelOptions()).profiles.filter(p => p.scope === 'global') } catch { /* keep previous options */ }
  } catch (e) {
    const message = e instanceof Error ? e.message : String(e)
    if (editor) editor.error = message
    else settings[scope].error = message
    pending.value = null
  } finally { busy.value = false }
}
onMounted(load)
</script>

<template>
  <div class="model-page">
    <PageHeader :title="tr('模型配置')">
      <button class="btn-primary" :disabled="loading || !!loadError" @click="addModel"><AppIcon name="add" />{{ tr('新增模型') }}</button>
    </PageHeader>
    <div v-if="loading" class="page-message" role="status">{{ tr('正在加载模型配置…') }}</div>
    <div v-else-if="loadError" class="page-message"><p role="alert">{{ tr(loadError) }}</p><button class="btn-ghost" @click="load">{{ tr('重试') }}</button></div>
    <ModelRegistry v-else class="configured-models" :rows="registryRows" :admin="isAdmin" @edit="editModel" />
    <BaseModal :open="dialogOpen" :title="tr(pending ? '保存全局配置' : dialogStep === 'choose' ? '新增模型' : dialogStep === 'defaults' ? '默认模型与请求设置' : selectedEditor?.scope ? '编辑模型' : '新增模型')" :width="dialogStep === 'configure' && !selectedPreset ? '640px' : '520px'" @close="closeDialog">
      <template v-if="pending">
        <p class="confirmation-message">{{ confirmMessage }}</p>
        <div class="dialog-actions"><button class="btn-ghost" :disabled="busy" @click="pending = null">{{ tr('取消') }}</button><button class="btn-primary" :disabled="busy" @click="persist(pending)">{{ tr(busy ? '保存中…' : '确定') }}</button></div>
      </template>
      <div v-else-if="dialogStep === 'choose'" class="provider-chooser">
        <p class="chooser-hint">{{ tr('选择服务商，或添加自定义模型') }}</p>
        <button v-for="preset in MODEL_PRESETS" :key="preset.id" class="provider-choice" :data-provider="preset.id" :disabled="scopes.every(scope => configured(preset.id, scope))" @click="addPreset(preset)">
          <ProviderIcon :provider="preset.id" />
          <span class="provider-info"><strong>{{ providerLabel(preset) }}</strong><small>{{ scopes.every(scope => configured(preset.id, scope)) ? tr('已配置，请在列表中编辑') : tr('{n} 个预置模型', { n: preset.models.length }) }}</small></span><AppIcon name="chevron_right" />
        </button>
        <button class="provider-choice custom-choice" data-provider="custom" @click="addCustom"><span class="provider-icon"><AppIcon name="add" /></span><span class="provider-info"><strong>{{ tr('自定义模型') }}</strong><small>{{ tr('配置接口地址与模型 ID') }}</small></span><AppIcon name="chevron_right" /></button>
      </div>
      <form v-else-if="dialogStep === 'configure' && selectedEditor" class="model-config-form" @submit.prevent="requestSave(selectedEditor)">
        <div class="editor-heading"><ProviderIcon v-if="selectedPreset" :provider="selectedPreset.id" :size="26" /><h2>{{ selectedPreset ? providerLabel(selectedPreset) : tr('自定义模型') }}</h2><span v-if="selectedEditor.scope" class="scope-hint">{{ scopeLabel(selectedEditor.scope) }}</span><button v-else type="button" class="back-button" @click="dialogStep = 'choose'">{{ tr('重新选择') }}</button></div>
        <ModelSourceEditor :source="selectedEditor.source" :preset="selectedPreset" :existing="selectedEditor.scope !== null" :scope="selectedEditor.scope ?? selectedEditor.target" :disabled="busy" />
        <div class="provider-actions" :class="{ editing: selectedEditor.scope !== null }">
          <label v-if="!selectedEditor.scope" class="save-target"><span>{{ tr('保存到') }}</span><select v-model="selectedEditor.target" class="select" :disabled="busy"><option v-for="scope in availableScopes(selectedEditor)" :key="scope" :value="scope">{{ scopeLabel(scope) }}</option></select></label>
          <button class="btn-primary" :disabled="busy">{{ tr(busy ? '保存中…' : '保存配置') }}</button>
        </div>
        <p v-if="selectedEditor.error" role="alert" class="editor-error">{{ modelSettingsError(selectedEditor.error) }}</p>
      </form>
      <section v-else-if="dialogStep === 'defaults'" class="defaults-panel">
        <form v-for="scope in scopes" :key="scope" class="settings-form" :data-scope="scope" @submit.prevent="requestSettings(scope)">
          <h3>{{ scopeLabel(scope) }}</h3>
          <label><span class="form-label">{{ tr('默认模型') }}</span><select v-model="settings[scope].defaultModel" class="select" :disabled="busy || !modelOptions(scope).length"><option v-if="!modelOptions(scope).length" value="">{{ tr('暂无可选模型') }}</option><option v-for="id in modelOptions(scope)" :key="id" :value="id">{{ id }}</option></select></label>
          <label v-if="scope === 'global'" class="timeout-field"><span class="form-label">{{ tr('请求超时（秒）') }}</span><input v-model.number="settings[scope].timeout" class="input" :disabled="busy" type="number" min="1" placeholder="60" /></label>
          <div class="provider-actions"><span></span><button class="btn-primary" :disabled="busy">{{ tr(busy ? '保存中…' : '保存设置') }}</button></div>
          <p v-if="settings[scope].error" role="alert" class="editor-error">{{ modelSettingsError(settings[scope].error) }}</p>
        </form>
      </section>
    </BaseModal>
  </div>
</template>

<style scoped>
.model-page { width: 100%; max-width: 1200px; margin: 0 auto; padding-bottom: 32px; color: var(--color-ink); font-size: 14px; line-height: 1.5; }
.configured-models { margin-top: 24px; }
.page-message { padding: 24px 0; color: var(--color-ink-muted); }
.chooser-hint { margin-bottom: 16px; color: var(--color-ink-muted); font-size: 13px; }
.provider-choice { display: flex; align-items: center; gap: 14px; width: 100%; padding: 14px 12px; border-bottom: 1px solid var(--color-line); text-align: left; }
.provider-choice:last-child { border-bottom: 0; }
.provider-choice:hover:not(:disabled) { background: var(--color-hover); }
.provider-choice:disabled { opacity: 0.55; cursor: not-allowed; }
.provider-choice > .app-icon { color: var(--color-ink-faint); }
.provider-icon { display: grid; place-items: center; flex: 0 0 36px; height: 36px; border: 1px solid var(--color-line); border-radius: 7px; color: var(--color-ink-secondary); font-weight: 600; background: var(--color-page); }
.provider-info { display: flex; flex-direction: column; flex: 1; min-width: 0; gap: 4px; }
.provider-info strong { font-weight: 500; }
.provider-info small { color: var(--color-ink-muted); font-size: 12px; }
.editor-heading { display: flex; align-items: center; flex-wrap: wrap; justify-content: space-between; gap: 12px; margin-bottom: 20px; }
.editor-heading h2 { flex: 1; font-size: 16px; font-weight: 600; }
.back-button { color: var(--color-primary); font-size: 12px; }
.provider-actions { display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 16px; margin-top: 24px; }
.provider-actions.editing { justify-content: flex-end; }
.save-target { display: flex; align-items: center; flex-wrap: wrap; gap: 10px; font-size: 12px; color: var(--color-ink-muted); }
.save-target .select { width: auto; max-width: 100%; }
.scope-hint { font-size: 12px; color: var(--color-ink-muted); }
.editor-error { margin-top: 12px; color: var(--color-danger); font-size: 13px; overflow-wrap: anywhere; }
.dialog-actions { display: flex; flex-wrap: wrap; justify-content: flex-end; gap: 12px; margin-top: 24px; }
.confirmation-message { color: var(--color-ink-secondary); }
.settings-form + .settings-form { border-top: 1px solid var(--color-line); margin-top: 24px; padding-top: 24px; }
.settings-form h3 { font-size: 14px; font-weight: 600; margin-bottom: 16px; }
.timeout-field { display: block; margin-top: 16px; }
:is(button, a):focus-visible { outline: 2px solid var(--color-primary); outline-offset: 2px; }
</style>
