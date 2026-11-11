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

export const getModelOptions = () => runtimeJson<ModelOptions>('/models/options')
export const getPersonalModels = () => runtimeJson<ModelConfigResult>('/models/personal')
export const getGlobalModels = () => runtimeJson<ModelConfigResult>('/models')

export function savePersonalModels(llm: LlmConfig, revision: number) {
  return runtimeJson<ModelConfigResult>('/models/personal', { method: 'PUT', body: JSON.stringify({ llm, revision }) })
}

export function saveGlobalModels(llm: LlmConfig, revision: number) {
  return runtimeJson<ModelConfigResult>('/models', { method: 'PUT', body: JSON.stringify({ llm, revision }) })
}
