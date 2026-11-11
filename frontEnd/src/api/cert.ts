import axios from 'axios'
import request from './request'
import { TOKEN_KEY } from './request'
import type {
  CertApplyVO,
  CertApproveResultVO,
  CertRevealPasswordVO,
  MyCertOverviewVO,
  PageResult,
  UserCertVO,
} from '@/types'

export interface CertApplyQuery {
  userName?: string
  status?: string
  pageNum?: number
  pageSize?: number
}

export interface UserCertQuery {
  userName?: string
  certType?: string
  status?: string
  pageNum?: number
  pageSize?: number
}

export interface CertApprovePayload {
  subjectCn: string
  subjectO?: string
  subjectOu?: string
  validDays: number
}

export function getMyCertOverview() {
  return request.get<MyCertOverviewVO>('/system/cert/mine')
}

export function applyCert(applyReason?: string) {
  return request.post<null>('/system/cert/mine/apply', { applyReason })
}

export function reissueCert(applyReason?: string) {
  return request.post<null>('/system/cert/mine/reissue', { applyReason })
}

export function listCertApplies(params: CertApplyQuery) {
  return request.get<PageResult<CertApplyVO>>('/system/cert/apply', { params })
}

export function listUserCerts(params: UserCertQuery) {
  return request.get<PageResult<UserCertVO>>('/system/cert', { params })
}

export function getCertDetail(certId: string | number) {
  return request.get<UserCertVO>(`/system/cert/${certId}`)
}

export function approveCertApply(applyId: string | number, payload: CertApprovePayload) {
  return request.post<CertApproveResultVO>(`/system/cert/apply/${applyId}/approve`, payload)
}

export function rejectCertApply(applyId: string | number, rejectReason?: string) {
  return request.post<null>(`/system/cert/apply/${applyId}/reject`, { rejectReason })
}

export function revokeCert(certId: string | number) {
  return request.put<null>(`/system/cert/${certId}/revoke`)
}

export async function downloadCertBundle(applyId: string | number) {
  const baseURL = import.meta.env.VITE_API_BASE || '/api'
  const token = localStorage.getItem(TOKEN_KEY)
  const res = await axios.get(`${baseURL}/system/cert/mine/download/${applyId}`, {
    responseType: 'blob',
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  const blob = res.data as Blob
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `client-cert-${applyId}.zip`
  a.click()
  URL.revokeObjectURL(url)
}

export function revealCertP12Password(applyId: string | number) {
  return request.post<CertRevealPasswordVO>(`/system/cert/mine/reveal-password/${applyId}`)
}
