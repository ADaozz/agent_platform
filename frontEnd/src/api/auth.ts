import request from './request'
import type { LoginResult, SysUserInfoVO } from '@/types'

export function login(userName: string, passWord: string) {
  return request.post<LoginResult>('/login', { userName, passWord })
}

export interface RegisterPayload {
  userName: string
  email: string
  passWord: string
  confirmPassWord: string
  code: string
}

/** 发送注册邮箱验证码 */
export function sendRegisterCode(email: string) {
  return request.post<null>('/register/code', { email })
}

/** 邮箱验证码注册（密码由后端哈希存储） */
export function register(data: RegisterPayload) {
  return request.post<null>('/register', data)
}

/**
 * 整页跳转 8443 触发 mTLS；GET 返回自动 POST 表单，由浏览器在 TLS 层提交客户端证。
 * 8443 只接受 https。回跳 Origin 仅在服务端白名单内生效，否则使用 CERT_LOGIN_PUBLIC_ORIGIN，不使用请求 Host。
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

export function certLoginAvailable() {
  return request.get<{ enabled: boolean }>('/login/cert/availability')
}

export function getUserInfo() {
  return request.get<SysUserInfoVO>('/user/info')
}
