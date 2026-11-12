export interface TagStyle {
  label: string
  cls: string
}

export const USER_STATUS_TAGS: Record<string, TagStyle> = {
  '0': { label: '已启用', cls: 'bg-emerald-50 text-emerald-700' },
  '1': { label: '已停用', cls: 'bg-red-50 text-red-700' },
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
