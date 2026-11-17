import { tr } from '@/composables/preferences'
import type { LlmConfig } from '@/api/agentRuntime'
import { modelIds, toForm, toLlm, validateForm, type SourceForm } from './modelConfigForm'

export type ModelScope = 'personal' | 'global'
export function cloneConfig<T>(value: T): T { return JSON.parse(JSON.stringify(value)) }

/** Replace one source against the saved snapshot, never against other drafts. */
export function mergeModelSource(saved: LlmConfig, source: SourceForm, scope: ModelScope): LlmConfig {
  const draft = { sources: [cloneConfig(source)], defaultModel: '', timeout: null, extra: {} }
  draft.defaultModel = modelIds(draft)[0] ?? ''
  const error = validateForm(draft, scope === 'personal')
  if (error) throw new Error(error)
  const group = toLlm(draft, scope === 'personal').models?.[source.name.trim()]
  if (!group) throw new Error('请填写 API Key')
  const merged = cloneConfig(saved)
  merged.models = { ...merged.models, [source.name.trim()]: group }
  const ids = modelIds(toForm(merged))
  if (!ids.includes(merged.default ?? '')) merged.default = ids[0] ?? ''
  return merged
}

/** Localize validation at render time so open errors follow language changes. */
export function modelSettingsError(message: string): string {
  const separator = message.indexOf('：')
  if (separator < 0) return tr(message)
  const label = message.slice(0, separator)
  const detail = message.slice(separator + 1)
  const source = label.startsWith('来源 ') ? tr('来源 {name}', { name: label.slice(3) }) : label
  const duplicate = /^模型 ID「(.+)」重复$/.exec(detail)
  const translated = duplicate ? tr('模型 ID「{id}」重复', { id: duplicate[1]! }) : tr(detail)
  return `${source}: ${translated}`
}
