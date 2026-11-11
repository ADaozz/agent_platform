import request from './request'
import type { DashboardOverviewVO } from '@/types'

export type DashboardScope = 'mine' | 'all'

export function getDashboardOverview(scope: DashboardScope = 'mine') {
  return request.get<DashboardOverviewVO>('/dashboard/overview', { params: { scope } })
}
