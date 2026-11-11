import request from './request'
import type { LoginSessionVO, PageResult } from '@/types'

export interface SessionQuery {
  userId?: string | number
  userName?: string
  pageNum?: number
  pageSize?: number
}

export function listSessions(params: SessionQuery) {
  return request.get<PageResult<LoginSessionVO>>('/system/session', { params })
}

export function listSessionHistory(userId: string | number) {
  return request.get<LoginSessionVO[]>('/system/session/history', { params: { userId } })
}

export function kickSession(sessionId: string) {
  return request.delete<null>(`/system/session/${sessionId}`)
}

export function logoutApi() {
  return request.post<null>('/logout')
}
