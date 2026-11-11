import request from './request'
import type { Id, JobEnabled, PageResult, SysJobVO } from '@/types'

export interface JobQuery {
  jobId?: Id
  jobName?: string
  enabled?: string
  pageNum?: number
  pageSize?: number
}

export function listJobs(params: JobQuery) {
  return request.get<PageResult<SysJobVO>>('/monitor/job', { params })
}

export interface JobEditBody {
  jobId: Id
  jobName: string
  cronExpression: string
  description?: string
  enabled?: JobEnabled
}

export function editJob(body: JobEditBody) {
  return request.put<null>('/monitor/job', body)
}

/** 快捷启用/停用（列表 Switch 专用，勿走整表更新） */
export function changeJobStatus(jobId: Id, enabled: JobEnabled) {
  return request.put<null>('/monitor/job/changeStatus', null, { params: { jobId, enabled } })
}

/** 手动执行（任务须已启用） */
export function runJob(jobId: Id) {
  return request.put<null>('/monitor/job/run', null, { params: { jobId } })
}
