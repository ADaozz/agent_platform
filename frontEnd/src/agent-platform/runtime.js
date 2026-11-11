// ITAM adapter: the Agent runtime is reached only through the ITAM backend proxy.
// Writes carry the Bearer token; EventSource, <img>, <a> and <iframe> rely on the
// HttpOnly read-only cookie issued by ensureRuntimeCookie().
import { TOKEN_KEY, expireLogin } from '@/api/request'

const GATEWAY = (import.meta.env.VITE_API_BASE || '/api') + '/agent-runtime'
export const API_BASE = GATEWAY + '/api'

export function authHeaders(headers = {}) {
  const token = localStorage.getItem(TOKEN_KEY)
  return token ? { ...headers, Authorization: 'Bearer ' + token } : headers
}

export async function runtimeFetch(path, options = {}) {
  const response = await fetch(API_BASE + path, { ...options, headers: authHeaders(options.headers) })
  if (response.status === 401) throw expireLogin()
  return response
}

export async function ensureRuntimeCookie() {
  const response = await fetch(GATEWAY + '/cookie', { method: 'POST', headers: authHeaders() })
  if (response.status === 401) throw expireLogin()
  if (!response.ok) throw new Error('Agent 服务鉴权失败 (' + response.status + ')')
}
