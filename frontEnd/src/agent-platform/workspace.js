// Shared between the embedded workspace and the platform sidebar, which hosts the
// conversation navigation. The sidebar stays mounted on every page, while the
// workspace only exists on /agent, so the sidebar sends commands it executes when ready.
import { ref } from 'vue'
import { runtimeFetch } from './runtime'
import { t } from './preferences'

export const sessions = ref([])
export const activeSessionId = ref(null)
export const workspaceView = ref('agents')
export const command = ref(null)
/** { session, resolve }: answered by the confirmation dialog mounted in the platform layout. */
export const deleteRequest = ref(null)

let sequence = 0
/** type: new | open (payload.id) | history | files | search */
export function dispatch(type, payload = {}) {
  command.value = { type, ...payload, seq: ++sequence }
}

export function sessionTitle(s) {
  const title = s.title || s.messages?.[0]?.content?.split('\n')[0] || t('New chat')
  return s.branched_from ? `${t('分支')}·${title}` : title
}

export function deletable(s) {
  return !['running', 'queued'].includes(s.status)
}

let sessionLoad = null
export function loadSessions() {
  if (sessionLoad) return sessionLoad
  sessionLoad = fetchSessions().finally(() => { sessionLoad = null })
  return sessionLoad
}

// Newest first: a turn in progress counts from when the user sent it, a settled one from
// when the Agent finished it. Sessions saved before turn end times existed use their last update.
const IN_PROGRESS = new Set(['queued', 'running', 'waiting_confirmation', 'waiting_human'])
export function sessionTime(s) {
  const value = (IN_PROGRESS.has(s.status) ? s.last_message_at : s.turn_ended_at) || s.updated_at || s.created_at
  return Date.parse(value) || 0
}

async function fetchSessions() {
  const response = await runtimeFetch('/agent/sessions?summary=true')
  if (!response.ok) throw new Error(t('请求失败，请检查输入配置'))
  sessions.value = (await response.json()).sort((a, b) => sessionTime(b) - sessionTime(a))
  return sessions.value
}

function confirmDelete(s) {
  deleteRequest.value?.resolve(false)
  return new Promise((resolve) => { deleteRequest.value = { session: s, resolve } })
}

export function answerDelete(ok) {
  const request = deleteRequest.value
  deleteRequest.value = null
  request?.resolve(ok)
}

/** Asks for confirmation; resolves true once the session is gone. */
export async function removeSession(s) {
  if (!deletable(s) || !(await confirmDelete(s))) return false
  // 204 has no body, so this cannot go through a JSON-parsing helper.
  const response = await runtimeFetch(`/agent/sessions/${s.id}`, { method: 'DELETE' })
  if (!response.ok) {
    const data = await response.json().catch(() => ({}))
    throw new Error(typeof data.detail === 'string' ? data.detail : t('删除对话失败'))
  }
  if (activeSessionId.value === s.id) dispatch('new')
  await loadSessions()
  return true
}
