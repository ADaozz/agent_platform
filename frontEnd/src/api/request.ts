import axios from 'axios'
import { toast } from '@/composables/toast'
import type { AjaxResult } from '@/types'

export const TOKEN_KEY = 'itam_token'
export const USER_KEY = 'itam_user'
export const SESSION_KEY = 'itam_session'

let expiring = false
/**
 * 登录失效（401）的唯一处理入口：必须先清掉本地登录态再跳转，
 * 否则路由守卫仍视为已登录，会在 /login 与业务页之间来回跳。
 */
export function expireLogin() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
  localStorage.removeItem(SESSION_KEY)
  if (!expiring && !location.pathname.startsWith('/login')) {
    expiring = true
    toast.error('登录已过期，请重新登录')
    location.href = '/login'
  }
  return new Error('登录已过期，请重新登录')
}

// 统一带 /api 前缀走同源请求：dev 由 Vite 代理转发（见 vite.config.ts），生产由 nginx 代理
const request = axios.create({
  baseURL: import.meta.env.VITE_API_BASE || '/api',
  timeout: 30000,
  // 雪花 ID（16 位以上整数）超出 JS 安全整数范围，先在原始 JSON 文本中转为字符串再解析
  transformResponse: [
    (data: unknown) => {
      if (typeof data !== 'string' || !data) return data
      try {
        return JSON.parse(data.replace(/([:[,]\s*)(\d{16,})(\s*[,}\]])/g, '$1"$2"$3'))
      } catch {
        return data
      }
    },
  ],
})

request.interceptors.request.use((config) => {
  const token = localStorage.getItem(TOKEN_KEY)
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

request.interceptors.response.use(
  (res) => {
    const body = res.data as AjaxResult
    if (body.code === 0) return body.data as never
    toast.error(body.msg || '请求失败')
    return Promise.reject(new Error(body.msg || '请求失败'))
  },
  (err) => {
    const status = err.response?.status
    if (status === 401) {
      expireLogin()
    } else if (status === 403) {
      toast.error('无权限访问')
    } else {
      toast.error(err.message || '网络错误')
    }
    return Promise.reject(err)
  },
)

// 拦截器已将 AjaxResult 解包为 data，这里修正返回值类型
export default request as unknown as {
  get<T>(url: string, config?: { params?: object }): Promise<T>
  post<T>(url: string, data?: unknown, config?: import('axios').AxiosRequestConfig): Promise<T>
  put<T>(url: string, data?: unknown, config?: { params?: object }): Promise<T>
  delete<T>(url: string): Promise<T>
}
