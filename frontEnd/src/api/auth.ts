import request from './request'
import type { LoginResult, SysUserInfoVO } from '@/types'

export function login(userName: string, passWord: string) {
  return request.post<LoginResult>('/login', { userName, passWord })
}

/**
 * 整页跳转 8443 触发 mTLS；GET 返回自动 POST 表单，由浏览器在 TLS 层提交客户端证。
 * 8443 只接受 https；origin 仅在后端白名单内时才会跳回当前前端，否则回到 https://host/login。
 */
export function loginByCert() {
  const { hostname, origin } = window.location
  window.location.href = `https://${hostname}:8443/login/cert?redirect=1&origin=${encodeURIComponent(origin)}`
}

function decodeBase64Url(value: string): string {
  const base64 = value.replace(/-/g, '+').replace(/_/g, '/')
  const pad = base64.length % 4 === 0 ? '' : '='.repeat(4 - (base64.length % 4))
  const binary = atob(base64 + pad)
  const bytes = Uint8Array.from(binary, (c) => c.charCodeAt(0))
  return new TextDecoder().decode(bytes)
}

/** 解析证书登录回跳携带的 #certLogin=<base64url JSON>；16 位以上的数字 ID 转成字符串以免丢精度 */
export function parseCertLoginPayload(payload: string): LoginResult {
  const json = decodeBase64Url(payload)
  return JSON.parse(json.replace(/([:[,]\s*)(\d{16,})(\s*[,}\]])/g, '$1"$2"$3'))
}

export function getUserInfo() {
  return request.get<SysUserInfoVO>('/user/info')
}
