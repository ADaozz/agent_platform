import request from './request'
import type { ApiTokenGrantGroup, ApiTokenVO, Id, PageResult, TokenAsset } from '@/types'

export interface TokenQuery {
  userId?: Id
  accessKey?: string
  tokenName?: string
  pageNum?: number
  pageSize?: number
}

export function listTokens(params: TokenQuery) {
  return request.get<PageResult<ApiTokenVO>>('/api/token', { params })
}

export function getTokensByUser(userId: Id) {
  return request.get<ApiTokenVO[]>(`/api/token/user/${userId}`)
}

/** 创建成功返回一次性 secretKey（SK），列表接口不再返回 */
export function addToken(body: { tokenName: string; detail: string; asset: TokenAsset[] }) {
  return request.post<ApiTokenVO>('/api/token', body)
}

/** 新建 Token 时可勾选的全部开放能力（含当前用户是否可授出） */
export function getGrantOptions() {
  return request.get<ApiTokenGrantGroup[]>('/api/token/grantOptions')
}

/** 按 accessKey 吊销 */
export function deleteToken(accessKey: string) {
  return request.delete<null>(`/api/token/${accessKey}`)
}
