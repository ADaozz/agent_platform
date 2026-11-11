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

export function getUserInfo() {
  return request.get<SysUserInfoVO>('/user/info')
}
