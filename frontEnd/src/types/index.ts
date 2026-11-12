export interface AjaxResult<T = unknown> {
  code: number
  msg: string
  data: T
}

export interface PageResult<T> {
  total: number
  rows: T[]
}

/** 后端雪花 ID 超出 JS 安全整数范围，响应层会将其转为字符串 */
export type Id = number | string

export interface OptionVO {
  id: Id
  label: string
}

export interface SysUserInfoVO {
  userId: Id
  username: string
  roles: OptionVO[]
  permissions: OptionVO[]
}

export interface LoginResult {
  token: string
  sessionId: string
  user: SysUserInfoVO
}

export interface SysUserVO {
  userId: Id
  userName: string
  status: string
  createTime: string | null
  updateTime: string | null
  lastLoginTime: string | null
  roles: OptionVO[]
}

export interface SysRoleVO {
  roleId: Id
  sysRole: string
  /** 已绑定的权限：id=permissionId，label=权限中文名（后端未维护时回退为权限标识） */
  permissions: OptionVO[]
}

export interface SysPermissionVO {
  permissionId: Id
  sysPermission: string
}

/**
 * 角色授权树节点。后端对 null 字段直接省略，因此菜单节点没有 permission/checked，
 * 权限节点没有 children，取值前务必判空。
 */
export interface PermTreeNode {
  /** 菜单节点为 menuId，权限节点为 permissionId（授权提交用的就是它） */
  id: Id
  /** 全局唯一键，menuId 与 permissionId 会撞号，列表渲染用它作 key */
  nodeKey: string
  name: string
  type: 'MENU' | 'PERMISSION'
  /** 仅权限节点：权限标识，如 system:user:list */
  permission?: string
  /** 仅权限节点：该角色是否已勾选 */
  checked?: boolean
  /** 仅菜单节点 */
  children?: PermTreeNode[]
}

export interface LoginSessionVO {
  sessionId: string
  userId: Id
  userName: string
  deviceName: string
  loginIp: string
  loginTime: string | null
  /** 0=在线 1=下线 */
  status: string
  /** 0=账密 1=证书 */
  loginType?: string
  current: boolean
}

export interface UserCertVO {
  certId: Id
  userId: Id
  userName?: string
  applyId: Id
  certType: 'sign' | 'encrypt' | string
  certFingerprint: string
  certSerial: string
  subjectDn: string
  issuerDn: string
  notBefore: string | null
  notAfter: string | null
  /** 0=有效 1=吊销 */
  status: string
  createTime: string | null
}

export interface CertApplyVO {
  applyId: Id
  userId: Id
  userName: string
  applyType: string
  status: string
  applyReason: string | null
  rejectReason: string | null
  subjectCn: string | null
  subjectO: string | null
  subjectOu: string | null
  validDays: number | null
  p12Password?: string | null
  /** 是否仍可领取 P12 密码（仅展示一次） */
  p12PasswordPending?: boolean
  downloadable: boolean
  createTime: string | null
  approveTime?: string | null
}

export interface MyCertOverviewVO {
  signCert: UserCertVO | null
  encryptCert: UserCertVO | null
  applies: CertApplyVO[]
}

export interface CertApproveResultVO {
  applyId: Id
  p12Password: string
  message: string
}

export interface CertRevealPasswordVO {
  applyId: Id
  p12Password: string
}
