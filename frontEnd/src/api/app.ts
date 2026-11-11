import request from './request'
import type { PageResult, VmAppVO } from '@/types'

export interface AppQuery {
  appId?: string
  appName?: string
  hostId?: string
  vmIp?: string
  appStatus?: string
  pageNum?: number
  pageSize?: number
}

export function listApps(params: AppQuery) {
  return request.get<PageResult<VmAppVO>>('/asset/app', { params })
}

export interface AppEditBody {
  appId: string
  appName: string
  deployPath: string
  appStatus: string
}

export function editApp(body: AppEditBody) {
  return request.put<null>('/asset/app', body)
}
