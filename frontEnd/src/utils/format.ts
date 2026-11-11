/** 统一时间显示：兼容 ISO（2026-08-21T08:41:58.000+00:00）与已格式化字符串 */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '-'
  if (!value.includes('T')) return value
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return value
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
}
