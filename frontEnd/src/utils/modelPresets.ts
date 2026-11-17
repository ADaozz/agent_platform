import type { ApiProtocol, ConfigForm, SourceForm } from '@/utils/modelConfigForm'
import { emptySource, isPresetSourceName } from '@/utils/modelConfigForm'

export type PresetId = 'deepseek' | 'qwen' | 'glm'

export interface PresetModel {
  key: string
  contextWindow: number
}

export interface ModelPreset {
  id: PresetId
  label: string
  baseUrl: string
  api: ApiProtocol
  efforts: string
  image: boolean
  models: PresetModel[]
  summary: string
}

const M = 1_000_000

/** 官方三家预设；用户只需填 API Key */
export const MODEL_PRESETS: ModelPreset[] = [
  {
    id: 'deepseek',
    label: 'DeepSeek',
    baseUrl: 'https://api.deepseek.com/v1',
    api: 'chat_completions',
    efforts: 'high, low, max',
    image: true,
    models: [
      { key: 'deepseek-flash', contextWindow: M },
      { key: 'deepseek-v4-pro', contextWindow: M },
    ],
    summary: 'Chat Completions · 思考 high/low/max · Flash 支持图片',
  },
  {
    id: 'qwen',
    label: '通义千问',
    baseUrl: 'https://dashscope.aliyuncs.com/compatible-mode/v1',
    api: 'chat_completions',
    efforts: 'high, low',
    image: true,
    models: [
      { key: 'qwen3.8-flash', contextWindow: M },
      { key: 'qwen3.7-plus', contextWindow: M },
      { key: 'qwen4-max', contextWindow: M },
    ],
    summary: '百炼兼容模式 · 思考 high/low · 支持图片',
  },
  {
    id: 'glm',
    label: '智谱 GLM',
    baseUrl: 'https://open.bigmodel.cn/api/paas/v4',
    api: 'chat_completions',
    efforts: 'max, high, low',
    image: true,
    models: [
      { key: 'glm-5.3', contextWindow: M },
      { key: 'glm-5.3-flash', contextWindow: M },
      { key: 'glm-5.3-flashx', contextWindow: M },
      { key: 'glm-5.3-flashx-legal', contextWindow: M },
    ],
    summary: 'Chat Completions · 思考 max/high/low · Flash 系支持图片',
  },
]

export { isPresetSourceName }

export function findSource(form: ConfigForm, id: PresetId): SourceForm | undefined {
  return form.sources.find((s) => s.name.trim() === id)
}

/** 将预设写入来源；已有同名来源时只补齐空字段，不覆盖用户已改内容（除非 reset） */
export function applyPreset(form: ConfigForm, id: PresetId, opts?: { reset?: boolean }): SourceForm {
  const preset = MODEL_PRESETS.find((p) => p.id === id)
  if (!preset) throw new Error(`未知预设: ${id}`)
  let source = findSource(form, id)
  if (!source) {
    source = emptySource()
    source.name = preset.id
    source.originalName = ''
    form.sources.push(source)
  }
  const reset = opts?.reset === true
  if (reset || !source.baseUrl.trim()) source.baseUrl = preset.baseUrl
  if (reset || !source.api) source.api = preset.api
  if (reset || !source.efforts.trim()) source.efforts = preset.efforts
  if (reset || (!source.image && preset.image)) source.image = preset.image
  if (reset || !source.models.some((m) => m.key.trim())) {
    source.models = preset.models.map((m) => ({ key: m.key, contextWindow: m.contextWindow, extra: {} }))
  }
  source.name = preset.id
  return source
}

export function ensurePresetSlots(form: ConfigForm) {
  for (const preset of MODEL_PRESETS) {
    if (!findSource(form, preset.id)) applyPreset(form, preset.id)
  }
}

export function customSources(form: ConfigForm) {
  return form.sources
    .map((source, index) => ({ source, index }))
    .filter(({ source }) => !isPresetSourceName(source.name))
}

export function removeSource(form: ConfigForm, index: number) {
  form.sources.splice(index, 1)
}
