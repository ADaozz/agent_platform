import { SECRET_MASK, type LlmConfig } from '@/api/agentRuntime'

export type ApiProtocol = 'responses' | 'chat_completions'

export interface ModelRow {
  key: string
  contextWindow: number | null
  /** 表单不展示的模型字段，保存时原样带回 */
  extra: Record<string, unknown>
}

export interface SourceForm {
  name: string
  originalName: string
  baseUrl: string
  /** 新填写的密钥；留空表示沿用已保存的密钥 */
  apiKey: string
  /** 已保存密钥的位置：来源级，或持有密钥的模型键（早期界面按模型保存） */
  savedKeyAt: 'source' | string[] | null
  api: ApiProtocol
  efforts: string
  image: boolean
  models: ModelRow[]
  extra: Record<string, unknown>
}

export interface ConfigForm {
  sources: SourceForm[]
  defaultModel: string
  timeout: number | null
  extra: Record<string, unknown>
}

const SHARED_FIELDS = ['base_url', 'api_key', 'api', 'input', 'reasoning_efforts']
const NAME_PATTERN = /^[A-Za-z0-9_.-]+$/

export function emptySource(): SourceForm {
  return {
    name: '', originalName: '', baseUrl: '', apiKey: '', savedKeyAt: null, api: 'chat_completions',
    efforts: '', image: false, models: [{ key: '', contextWindow: null, extra: {} }], extra: {},
  }
}

function without(value: Record<string, any>, fields: string[]) {
  const result = { ...value }
  for (const field of fields) delete result[field]
  return result
}

export function toForm(llm: LlmConfig): ConfigForm {
  const { default: defaultModel = '', timeout, models = {}, ...extra } = llm
  const sources = Object.entries(models as Record<string, any>).map(([name, raw]): SourceForm => {
    const { models: items = {}, ...group } = raw || {}
    const entries = Object.entries(items as Record<string, any>)
    const pick = (field: string) => group[field] ?? entries.map(([, item]) => item?.[field]).find((v) => v !== undefined)
    let apiKey = ''
    let savedKeyAt: SourceForm['savedKeyAt'] = null
    if (group.api_key === SECRET_MASK) savedKeyAt = 'source'
    else if (typeof group.api_key === 'string') apiKey = group.api_key
    else {
      const holders = entries.filter(([, item]) => item?.api_key === SECRET_MASK).map(([key]) => key)
      if (holders.length) savedKeyAt = holders
      else apiKey = entries.map(([, item]) => item?.api_key).find((v) => typeof v === 'string') ?? ''
    }
    const input = pick('input')
    return {
      name, originalName: name, baseUrl: pick('base_url') ?? '', apiKey, savedKeyAt,
      api: pick('api') === 'chat_completions' ? 'chat_completions' : 'responses',
      efforts: (pick('reasoning_efforts') ?? []).join(', '),
      image: Array.isArray(input) && input.includes('image'),
      models: entries.map(([key, item]) => {
        const { context_window, ...rest } = item || {}
        return { key, contextWindow: context_window ?? null, extra: without(rest, SHARED_FIELDS) }
      }),
      extra: without(group, SHARED_FIELDS),
    }
  })
  return { sources, defaultModel, timeout: typeof timeout === 'number' ? timeout : null, extra }
}

export function modelIds(form: ConfigForm) {
  return form.sources.flatMap((s) => s.models.filter((m) => m.key.trim()).map((m) => `${s.name.trim()}/${m.key.trim()}`))
}

export function validateForm(form: ConfigForm, personal: boolean): string | null {
  const names = new Set<string>()
  for (const [index, s] of form.sources.entries()) {
    const label = `来源 ${s.name || index + 1}`
    const name = s.name.trim()
    if (!NAME_PATTERN.test(name)) return `${label}：名称只能使用字母、数字、下划线、点或短横线`
    if (names.has(name)) return `${label}：来源名称重复`
    names.add(name)
    if (!/^https?:\/\//.test(s.baseUrl.trim())) return `${label}：接口地址必须以 http:// 或 https:// 开头`
    const key = s.apiKey.trim()
    if (personal && key.includes('${')) return `${label}：个人模型不能引用服务器环境变量，请直接填写 API Key`
    if (!key) {
      if (!s.savedKeyAt) return `${label}：请填写 API Key`
      if (name !== s.originalName) return `${label}：修改来源名称后需重新填写 API Key`
      if (Array.isArray(s.savedKeyAt) && s.savedKeyAt.some((k) => !s.models.some((m) => m.key.trim() === k))) {
        return `${label}：修改模型 ID 后需重新填写 API Key`
      }
    }
    if (!s.models.length) return `${label}：至少需要一个模型`
    const keys = new Set<string>()
    for (const m of s.models) {
      const id = m.key.trim()
      if (!id || id.includes('/')) return `${label}：模型 ID 不能为空且不能包含 /`
      if (keys.has(id)) return `${label}：模型 ID「${id}」重复`
      keys.add(id)
      if (m.contextWindow != null && (!Number.isInteger(m.contextWindow) || m.contextWindow < 0)) return `${label}：上下文窗口必须是非负整数`
    }
  }
  if (form.sources.length && !modelIds(form).includes(form.defaultModel)) return '请选择默认模型'
  return null
}

export function toLlm(form: ConfigForm, personal: boolean): LlmConfig {
  const models: Record<string, any> = {}
  for (const s of form.sources) {
    const items: Record<string, any> = {}
    for (const m of s.models) {
      const item: Record<string, any> = { ...m.extra }
      if (m.contextWindow) item.context_window = m.contextWindow
      items[m.key.trim()] = item
    }
    const group: Record<string, any> = {
      ...s.extra, base_url: s.baseUrl.trim(), api: s.api, input: s.image ? ['text', 'image'] : ['text'],
    }
    const efforts = s.efforts.split(/[,，\s]+/).map((v) => v.trim()).filter(Boolean)
    if (efforts.length) group.reasoning_efforts = efforts
    const key = s.apiKey.trim()
    if (key) group.api_key = key
    else if (s.savedKeyAt === 'source') group.api_key = SECRET_MASK
    else if (Array.isArray(s.savedKeyAt)) for (const holder of s.savedKeyAt) items[holder].api_key = SECRET_MASK
    group.models = items
    models[s.name.trim()] = group
  }
  // 个人配置只允许 default 与 models 两个字段
  const llm: LlmConfig = personal ? {} : { ...form.extra }
  llm.default = form.sources.length ? form.defaultModel : ''
  llm.models = models
  if (!personal && form.timeout) llm.timeout = form.timeout
  return llm
}
