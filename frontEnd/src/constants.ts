import type { LifecycleStatus } from '@/types'

export interface TagStyle {
  label: string
  cls: string
}

export const LIFECYCLE_ORDER: LifecycleStatus[] = [
  'creating',
  'running',
  'stopped',
  'pending_delete',
  'destroyed',
]

export function nextLifecycle(status: LifecycleStatus): LifecycleStatus | null {
  const idx = LIFECYCLE_ORDER.indexOf(status)
  if (idx < 0 || idx >= LIFECYCLE_ORDER.length - 1) return null
  return LIFECYCLE_ORDER[idx + 1]!
}

export const LIFECYCLE_TAGS: Record<string, TagStyle> = {
  creating: { label: '创建中', cls: 'bg-blue-50 text-blue-700' },
  running: { label: '运行中', cls: 'bg-emerald-50 text-emerald-700' },
  stopped: { label: '已停止', cls: 'bg-gray-100 text-gray-600' },
  pending_delete: { label: '待删除', cls: 'bg-orange-50 text-orange-700' },
  destroyed: { label: '已销毁', cls: 'bg-red-50 text-red-700' },
}

export const APP_STATUS_TAGS: Record<string, TagStyle> = {
  running: { label: '运行中', cls: 'bg-emerald-50 text-emerald-700' },
  stopped: { label: '已停止', cls: 'bg-gray-100 text-gray-600' },
}

export const USER_STATUS_TAGS: Record<string, TagStyle> = {
  '0': { label: '已启用', cls: 'bg-emerald-50 text-emerald-700' },
  '1': { label: '已停用', cls: 'bg-red-50 text-red-700' },
}

export const TOKEN_STATUS_TAGS: Record<string, TagStyle> = {
  '0': { label: '有效', cls: 'bg-emerald-50 text-emerald-700' },
  '1': { label: '已吊销', cls: 'bg-red-50 text-red-700' },
}

export const SESSION_STATUS_TAGS: Record<string, TagStyle> = {
  '0': { label: '在线', cls: 'bg-emerald-50 text-emerald-700' },
  '1': { label: '下线', cls: 'bg-red-50 text-red-700' },
}

export const LOGIN_TYPE_TAGS: Record<string, TagStyle> = {
  '0': { label: '账密', cls: 'bg-blue-50 text-blue-700' },
  '1': { label: '证书', cls: 'bg-violet-50 text-violet-700' },
}

export const CERT_STATUS_TAGS: Record<string, TagStyle> = {
  '0': { label: '有效', cls: 'bg-emerald-50 text-emerald-700' },
  '1': { label: '已吊销', cls: 'bg-red-50 text-red-700' },
}

export const CERT_APPLY_STATUS_TAGS: Record<string, TagStyle> = {
  pending: { label: '待审批', cls: 'bg-amber-50 text-amber-700' },
  approved: { label: '已通过', cls: 'bg-emerald-50 text-emerald-700' },
  rejected: { label: '已拒绝', cls: 'bg-red-50 text-red-700' },
}

export const CERT_TYPE_LABELS: Record<string, string> = {
  sign: '签名证书',
  encrypt: '加密证书',
}

export const TOKEN_ASSET_LABELS: Record<string, string> = {
  vm: '虚拟机·查询',
  app: '应用服务·查询',
  'vm:list': '虚拟机·查询',
  'vm:add': '虚拟机·新增',
  'vm:edit': '虚拟机·修改',
  'vm:delete': '虚拟机·删除',
  'app:list': '应用服务·查询',
  'app:add': '应用服务·新增',
  'app:edit': '应用服务·修改',
  'app:delete': '应用服务·删除',
}

/** 定时任务最近执行状态光点（色值按接口文档约定） */
export const JOB_STATUS_DOTS: Record<string, { label: string; dotCls: string }> = {
  '0': { label: '未执行', dotCls: 'bg-[#909399]' },
  '1': { label: '正在执行', dotCls: 'bg-[#409EFF] animate-pulse' },
  '2': { label: '执行成功', dotCls: 'bg-[#67C23A]' },
  '3': { label: '执行失败', dotCls: 'bg-[#F56C6C]' },
}
export const ENV_TAGS: Record<string, TagStyle> = {
  prod: { label: '生产', cls: 'bg-red-50 text-red-700' },
  dev: { label: '开发', cls: 'bg-blue-50 text-blue-700' },
  test: { label: '测试', cls: 'bg-amber-50 text-amber-700' },
}

export const ZONE_LABELS: Record<string, string> = {
  idc: 'IDC 机房',
  cfdc: 'CFDC',
}

export const ENV_OPTIONS = [
  { value: 'prod', label: '生产' },
  { value: 'dev', label: '开发' },
  { value: 'test', label: '测试' },
]

export const ZONE_OPTIONS = [
  { value: 'idc', label: 'IDC 机房' },
  { value: 'cfdc', label: 'CFDC' },
]
