<script setup lang="ts">
import { computed } from 'vue'
import { sortReasoningEfforts } from '@/utils/reasoningEfforts'
import AppIcon from '@/components/AppIcon.vue'
import { tr } from '@/composables/preferences'
import type { SourceForm } from '@/utils/modelConfigForm'
import type { ModelPreset } from '@/utils/modelPresets'

const props = defineProps<{ source: SourceForm; preset?: ModelPreset; existing: boolean; disabled: boolean; scope: 'personal' | 'global' }>()
const effortText = computed(() => sortReasoningEfforts(props.source.efforts.split(/[,，\s]+/).filter(Boolean)).join(', '))
</script>

<template>
  <div class="source-fields">
    <div v-if="preset" class="preset-models-field">
      <span class="form-label">{{ tr('模型') }}</span>
      <div class="preset-models" :class="{ single: source.models.length === 1 }">
        <span v-for="model in source.models" :key="model.key" class="preset-model-name">{{ model.key }}</span>
      </div>
    </div>
    <div v-else class="custom-fields">
      <label><span class="form-label">{{ tr('来源名称') }}</span><input v-model="source.name" class="input" :disabled="existing || disabled" :placeholder="tr('如 openai')" /></label>
      <label><span class="form-label">{{ tr('接口地址') }}</span><input v-model="source.baseUrl" class="input" :disabled="disabled" placeholder="https://api.example.com/v1" /></label>
      <label><span class="form-label">{{ tr('接口协议') }}</span><select v-model="source.api" class="select" :disabled="disabled"><option value="chat_completions">Chat Completions</option><option value="responses">Responses</option></select></label>
      <label><span class="form-label">{{ tr('思考强度') }}</span><input :value="effortText" @change="source.efforts = ($event.target as HTMLInputElement).value" class="input" :disabled="disabled" placeholder="low, medium, high" /></label>
      <label class="image-option"><input v-model="source.image" type="checkbox" :disabled="disabled" /> {{ tr('支持图片输入') }}</label>
      <div class="custom-models">
        <span class="form-label">{{ tr('模型') }}</span>
        <div v-for="(row, index) in source.models" :key="index" class="model-row">
          <input v-model="row.key" class="input" :disabled="disabled" :aria-label="tr('模型 ID')" :placeholder="tr('模型 ID')" />
          <input v-model.number="row.contextWindow" class="input" :disabled="disabled" type="number" min="0" :aria-label="tr('上下文窗口（可选）')" :placeholder="tr('上下文窗口（可选）')" />
          <button type="button" class="btn-ghost" :disabled="disabled || source.models.length === 1" :aria-label="tr('删除模型')" @click="source.models.splice(index, 1)"><AppIcon name="delete" /></button>
        </div>
        <button type="button" class="source-link" :disabled="disabled" @click="source.models.push({ key: '', contextWindow: null, extra: {} })">{{ tr('添加模型') }}</button>
      </div>
    </div>
    <label class="key-label">
      <span class="form-label">API Key</span>
      <input v-model="source.apiKey" class="input" type="password" autocomplete="new-password" :disabled="disabled" :placeholder="source.savedKeyAt ? tr('已保存，留空则不修改') : scope === 'personal' ? tr('输入新的 API Key') : tr('API Key 或 ${ENV_NAME}')" />
    </label>
    <p v-if="preset" class="source-hint">{{ tr('接口和模型参数由平台预置') }}</p>
  </div>
</template>

<style scoped>
.source-fields { min-width: 0; }
.preset-models-field { margin-bottom: 20px; }
.preset-models { display: flex; flex-wrap: wrap; gap: 8px; }
.preset-model-name { padding: 4px 8px; border: 1px solid var(--color-line); border-radius: 4px; color: var(--color-ink-secondary); font-size: 12px; overflow-wrap: anywhere; }
.preset-models.single .preset-model-name { padding: 0; border: 0; font-size: 14px; color: var(--color-ink); }
.custom-fields { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 16px; margin-bottom: 20px; }
.custom-models { grid-column: 1 / -1; }
.model-row { display: grid; grid-template-columns: minmax(0, 1fr) minmax(0, 1fr) auto; gap: 8px; margin-bottom: 8px; }
.model-row .btn-ghost { padding-inline: 8px; }
.image-option { display: flex; align-items: center; gap: 8px; color: var(--color-ink-secondary); font-size: 13px; }
.key-label { display: block; }
.source-hint { margin-top: 12px; color: var(--color-ink-faint); font-size: 12px; }
.source-link { color: var(--color-primary); font-size: 12px; }
@media (max-width: 640px) { .custom-fields { grid-template-columns: 1fr; } .model-row { grid-template-columns: minmax(0, 1fr) auto; } .model-row input:first-child { grid-column: 1 / -1; } }
</style>
