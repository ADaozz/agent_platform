<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { tr } from '@/composables/preferences'
import type { IconName } from '@/icons'
import {
  activeSessionId,
  deletable,
  dispatch,
  loadSessions,
  recentSessions,
  sessions,
  sessionTitle,
  workspaceView,
  // @ts-ignore: shared with the JavaScript workspace UI
} from '@/agent-platform/workspace'

const props = defineProps<{ open: boolean }>()

const route = useRoute()
const router = useRouter()
const onAgent = computed(() => route.path === '/agent')

const actions: { type: string; title: string; icon: IconName }[] = [
  { type: 'new', title: '新建对话', icon: 'add' },
  { type: 'history', title: '历史对话', icon: 'history' },
  { type: 'files', title: '全局文件', icon: 'folder' },
]

function actionActive(type: string) {
  if (!onAgent.value) return false
  // Recent rows are hidden when collapsed; the Agent entry carries their selection.
  if (type === 'new') return workspaceView.value === 'agents' && (!activeSessionId.value || !props.open)
  return type === workspaceView.value
}

/** The workspace only exists on /agent; it picks up the command once mounted. */
async function go(type: string, payload: Record<string, unknown> = {}) {
  if (!onAgent.value) await router.push('/agent')
  dispatch(type, payload)
}

// On /agent the workspace keeps the list fresh; elsewhere the sidebar polls by itself.
let timer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  loadSessions().catch(() => {})
  timer = setInterval(() => {
    if (!onAgent.value) loadSessions().catch(() => {})
  }, 5000)
})
onUnmounted(() => clearInterval(timer))
</script>

<template>
  <div>
    <button
      v-for="a in actions"
      :key="a.type"
      type="button"
      class="rail-item"
      :class="{ 'rail-item-active': actionActive(a.type) }"
      :title="tr(a.title)"
      @click="go(a.type)"
    >
      <AppIcon :name="a.icon" />
      <span v-if="open" class="flex-1 truncate text-left">{{ tr(a.title) }}</span>
    </button>
  </div>

  <div v-if="open" class="mt-5">
    <div class="recent-head">
      <span class="flex-1">{{ tr('最近对话') }}</span>
    </div>
    <button
      v-for="s in recentSessions"
      :key="s.id"
      type="button"
      class="rail-item recent-row"
      :class="{ 'recent-row-active': onAgent && workspaceView === 'agents' && activeSessionId === s.id }"
      @click="go('open', { id: s.id })"
    >
      <span class="status-lamp" :class="s.status" />
      <span class="min-w-0 flex-1 truncate text-left">{{ sessionTitle(s) }}</span>
      <span v-if="!deletable(s)" class="spinner" />
    </button>
    <p v-if="!recentSessions.length" class="recent-empty">{{ tr(sessions.length ? '近 7 天暂无对话' : '暂无对话') }}</p>
  </div>
</template>

<style scoped>
.recent-head {
  display: flex;
  align-items: center;
  gap: 0.625rem;
  height: 1.75rem;
  padding: 0 0.875rem 0 1.25rem;
  font-size: 11.5px;
  letter-spacing: 0.04em;
  white-space: nowrap;
  color: var(--chrome-ink-3);
}
.recent-row {
  height: 2rem;
  gap: 0.5rem;
  padding-right: 0.75rem;
  font-size: 12.5px;
}
.recent-row-active {
  background-color: var(--chrome-glass);
  color: var(--chrome-ink);
}
.recent-empty {
  padding: 0.5rem 1.25rem;
  font-size: 12px;
  color: var(--chrome-ink-3);
}
/* 状态指示灯：颜色承担状态语义 */
.status-lamp {
  height: 6px;
  width: 6px;
  margin: 0 3px;
  border-radius: 50%;
  flex-shrink: 0;
  background-color: var(--chrome-ink-3);
}
.status-lamp.completed {
  background-color: var(--color-success);
}
.status-lamp.running,
.status-lamp.queued {
  background-color: var(--color-warning);
}
.status-lamp.failed,
.status-lamp.interrupted {
  background-color: var(--color-danger);
}
.spinner {
  height: 0.75rem;
  width: 0.75rem;
  flex-shrink: 0;
  border-radius: 9999px;
  border: 1.5px solid var(--chrome-ink-3);
  border-top-color: var(--chrome-signal);
  animation: agent-nav-spin 0.9s linear infinite;
}
@keyframes agent-nav-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
