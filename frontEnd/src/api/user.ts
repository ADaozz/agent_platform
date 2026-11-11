import request from './request'
import type { Id, PageResult, SysUserVO } from '@/types'

export interface UserQuery {
  userId?: number
  userName?: string
  status?: string
  roleId?: number
  pageNum?: number
  pageSize?: number
}

export function listUsers(params: UserQuery) {
  return request.get<PageResult<SysUserVO>>('/system/user', { params })
}

export interface UserAddBody {
  userName: string
  passWord: string
  status?: string
  roleIds?: Id[]
}

export function addUser(body: UserAddBody) {
  return request.post<null>('/system/user', body)
}

export interface UserEditBody {
  userId: Id
  userName: string
  passWord?: string
  status?: string
}

export function editUser(body: UserEditBody) {
  return request.put<null>('/system/user', body)
}

export function authRole(userId: Id, roleIds: Id[]) {
  return request.put<null>('/system/user/authRole', { userId, roleIds })
}

export function deleteUser(userId: Id) {
  return request.delete<null>(`/system/user/${userId}`)
}
