import { TOKEN_KEY, expireLogin } from './request'

const BASE = (import.meta.env.VITE_API_BASE || '/api') + '/agent-runtime/api'

/** 已保存密钥在读取接口中的占位符，原样回传即保持不变 */
export const SECRET_MASK = '__UNCHANGED_SECRET__'

export interface ModelProfile {
  id: string
  model: string
  api: string
  context_window: number
  reasoning_efforts: string[]
  default_reasoning_effort: string | null
  configured: boolean
  scope?: 'global' | 'personal'
}

export type LlmConfig = Record<string, any> & { default?: string; models?: Record<string, any> }

export interface ModelConfigResult {
  llm: LlmConfig
  revision: number
  profiles: ModelProfile[]
}

export interface ModelOptions {
  default: string
  profiles: ModelProfile[]
  default_reasoning_effort: string | null
}

function errorMessage(data: any, status: number) {
  if (typeof data?.detail === 'string') return data.detail
  if (Array.isArray(data?.detail)) return data.detail.map((d: any) => d.msg).join('；')
  return data?.msg || `Agent 服务请求失败 (${status})`
}

async function runtimeJson<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) headers.set('Authorization', 'Bearer ' + token)
  if (init.body) headers.set('Content-Type', 'application/json')
  const response = await fetch(BASE + path, { ...init, headers, cache: 'no-store' })
  if (response.status === 401) throw expireLogin()
  const data = await response.json().catch(() => ({}))
  if (!response.ok) throw new Error(errorMessage(data, response.status))
  return data as T
}

export interface UsageRateBand {
  cache_hit: number
  cache_miss: number
  output: number
}

export interface UsageDayRow {
  date: string
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens: number
  total_tokens: number
  calls: number
  peak_calls: number
  off_peak_calls: number
  cost_cny: number
}

export interface UsageSessionRow {
  session_id: string
  title: string
  model_id: string | null
  input_tokens: number
  output_tokens: number
  cache_read_input_tokens: number
  total_tokens: number
  calls: number
  peak_calls: number
  off_peak_calls: number
  cost_cny: number
  last_at: string | null
  updated_at: string | null
}

export interface UsageOverview {
  filters?: { providers: string[]; models: Array<{ provider: string; id: string }> }
  days: number
  currency: string
  cost_note: string
  pricing_source?: string
  rates_cny_per_m: Record<string, { off_peak: UsageRateBand; peak: UsageRateBand }>
  peak_windows?: {
    timezone: string
    weekdays: string
    hours: string[]
    note: string
  }
  totals: {
    input_tokens: number
    output_tokens: number
    cache_read_input_tokens: number
    total_tokens: number
    calls: number
    peak_calls: number
    off_peak_calls: number
    cost_cny: number
    sessions: number
  }
  daily: UsageDayRow[]
  sessions: UsageSessionRow[]
}

export interface CapabilityTool {
  name: string
  enabled: boolean
  description?: string
}

export interface CapabilitySkill {
  id: string
  name: string
  description: string
  source: 'feature' | 'platform'
  feature_id?: string | null
  enabled: boolean
  available: boolean
}

export interface PlatformCapabilities {
  revision: number
  editable: boolean
  core_tools: CapabilityTool[]
  tools: CapabilityTool[]
  skills: CapabilitySkill[]
}

export interface CapabilityMounts {
  revision: number
  core_tools: Record<string, boolean>
  tools: Record<string, boolean>
  skill_bindings: Record<string, boolean>
}

export const getPlatformCapabilities = () => runtimeJson<PlatformCapabilities>('/platform/capabilities')
export const savePlatformCapabilities = (mounts: CapabilityMounts) =>
  runtimeJson<PlatformCapabilities>('/platform/capabilities', { method: 'PUT', body: JSON.stringify(mounts) })

export const getModelOptions = () => runtimeJson<ModelOptions>('/models/options')
export const getPersonalModels = () => runtimeJson<ModelConfigResult>('/models/personal')
export const getGlobalModels = () => runtimeJson<ModelConfigResult>('/models')
export function getUsageOverview(days = 30, filters: { provider?: string; model?: string } = {}) {
  const query = new URLSearchParams({ days: String(days) })
  if (filters.provider) query.set('provider', filters.provider)
  if (filters.model) query.set('model', filters.model)
  return runtimeJson<UsageOverview>(`/agent/usage/overview?${query}`)
}

export function savePersonalModels(llm: LlmConfig, revision: number) {
  return runtimeJson<ModelConfigResult>('/models/personal', { method: 'PUT', body: JSON.stringify({ llm, revision }) })
}

export function saveGlobalModels(llm: LlmConfig, revision: number) {
  return runtimeJson<ModelConfigResult>('/models', { method: 'PUT', body: JSON.stringify({ llm, revision }) })
}
