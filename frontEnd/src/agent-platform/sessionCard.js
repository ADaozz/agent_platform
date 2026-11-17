/** Session-card dates are based on creation time, independently of list ordering. */
export function relativeCreation(value, locale = 'zh', now = Date.now()) {
  const timestamp = Date.parse(value)
  if (!Number.isFinite(timestamp)) return '—'
  const seconds = Math.max(0, Math.floor((now - timestamp) / 1000))
  if (seconds < 10) return locale === 'zh' ? '刚刚' : 'just now'
  if (seconds < 60) return locale === 'zh' ? `${seconds} 秒前` : `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return locale === 'zh' ? `${minutes} 分钟前` : `${minutes} min ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return locale === 'zh' ? `${hours} 小时前` : `${hours} ${hours === 1 ? 'hour' : 'hours'} ago`
  const days = Math.floor(hours / 24)
  if (days < 30) return locale === 'zh' ? `${days} 天前` : `${days} ${days === 1 ? 'day' : 'days'} ago`
  return creationDate(value, locale)
}

export function creationDate(value, locale = 'zh') {
  if (!value) return '—'
  const date = new Date(value)
  if (!Number.isFinite(date.getTime())) return '—'
  return new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
    year: 'numeric', month: locale === 'zh' ? 'long' : 'short', day: 'numeric',
  }).format(date)
}

export function taskDuration(session, locale = 'zh', now = Date.now()) {
  if (typeof session.task_duration_ms !== 'number' || !Number.isFinite(session.task_duration_ms)) return '—'
  const since = Date.parse(session.task_running_since)
  const active = session.status === 'running' && Number.isFinite(since) ? Math.max(0, now - since) : 0
  const seconds = Math.floor(Math.max(0, session.task_duration_ms + active) / 1000)
  if (seconds < 60) return locale === 'zh' ? `${seconds} 秒` : `${seconds}s`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return locale === 'zh' ? `${minutes} 分 ${seconds % 60} 秒` : `${minutes}m ${seconds % 60}s`
  const hours = Math.floor(minutes / 60)
  return locale === 'zh' ? `${hours} 小时 ${minutes % 60} 分` : `${hours}h ${minutes % 60}m`
}

export function taskCost(session, locale = 'zh') {
  const cost = session.task_cost_cny
  if (typeof cost !== 'number' || !Number.isFinite(cost) || cost < 0) return '—'
  const digits = cost > 0 && cost < 0.01 ? 4 : 2
  return '¥' + new Intl.NumberFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
    minimumFractionDigits: digits, maximumFractionDigits: digits,
  }).format(cost)
}
