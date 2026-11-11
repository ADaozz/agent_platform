import request from './request'
import type { PageResult, VmHostVO } from '@/types'

export interface VmQuery {
  hostId?: string
  hostName?: string
  vmIp?: string
  lifecycleStatus?: string
  ownerUserId?: number
  networkZone?: string
  env?: string
  pageNum?: number
  pageSize?: number
}

export function listVms(params: VmQuery) {
  return request.get<PageResult<VmHostVO>>('/asset/vm', { params })
}

export interface VmEditBody {
  hostId: string
  hostName: string
  osType: string
  osVersion?: string | null
  vmIp?: string | null
  cpuCores?: number | null
  memoryGb?: number | null
  diskGb?: number | null
  physicalHostIp?: string | null
  lifecycleStatus?: string
  networkZone: string
  env: string
  remark?: string | null
}

export function editVm(body: VmEditBody) {
  return request.put<null>('/asset/vm', body)
}
