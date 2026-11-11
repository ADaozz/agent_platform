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
  return s.title || s.messages?.[0]?.content?.split('\n')[0] || t('New chat')
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

async function fetchSessions() {
  const response = await runtimeFetch('/agent/sessions?summary=true')
  if (!response.ok) throw new Error(t('请求失败，请检查输入配置'))
  sessions.value = await response.json()
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
