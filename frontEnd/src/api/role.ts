import request from './request'
import type { Id, OptionVO, PageResult, PermTreeNode, SysPermissionVO, SysRoleVO } from '@/types'

// ---------- 角色 ----------

export interface RoleQuery {
  roleId?: Id
  sysRole?: string
  pageNum?: number
  pageSize?: number
}

export function listRoles(params: RoleQuery) {
  return request.get<PageResult<SysRoleVO>>('/system/role', { params })
}

export function getRoleOptions() {
  return request.get<OptionVO[]>('/system/role/options')
}

/** 新增角色，可同时绑定权限（不传 permissionIds 表示空权限） */
export function addRole(body: { sysRole: string; permissionIds?: Id[] }) {
  return request.post<null>('/system/role', body)
}

/** 修改角色标识 */
export function editRole(body: { roleId: Id; sysRole: string }) {
  return request.put<null>('/system/role', body)
}

/** 覆盖式分配权限；空数组表示清空权限 */
export function authPerm(roleId: Id, permissionIds: Id[]) {
  return request.put<null>('/system/role/authPerm', { roleId, permissionIds })
}

/** 删除未绑定用户的角色 */
export function deleteRole(roleId: Id) {
  return request.delete<null>(`/system/role/${roleId}`)
}

// ---------- 权限 ----------

export interface PermissionQuery {
  permissionId?: Id
  sysPermission?: string
  pageNum?: number
  pageSize?: number
}

export function listPermissions(params: PermissionQuery) {
  return request.get<PageResult<SysPermissionVO>>('/system/permission', { params })
}

export function getPermissionOptions() {
  return request.get<OptionVO[]>('/system/permission/options')
}

/**
 * 角色授权树（菜单分组 + 权限叶子），仅 admin 可调用。
 * 传 roleId 回显该角色的勾选状态，不传则全部未勾选（新增角色场景）。
 */
export function getPermTree(roleId?: Id) {
  return request.get<PermTreeNode[]>('/system/menu/permTree', { params: { roleId } })
}
