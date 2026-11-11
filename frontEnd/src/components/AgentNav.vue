<script setup lang="ts">
import { computed, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import AppIcon from '@/components/AppIcon.vue'
import { toast } from '@/composables/toast'
import { tr } from '@/composables/preferences'
import type { IconName } from '@/icons'
import {
  activeSessionId,
  deletable,
  dispatch,
  loadSessions,
  removeSession,
  sessions,
  sessionTitle,
  workspaceView,
  // @ts-ignore: shared with the JavaScript workspace UI
} from '@/agent-platform/workspace'

defineProps<{ open: boolean }>()

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
  if (type === 'new') return workspaceView.value === 'agents' && !activeSessionId.value
  return type === workspaceView.value
}

/** The workspace only exists on /agent; it picks up the command once mounted. */
async function go(type: string, payload: Record<string, unknown> = {}) {
  if (!onAgent.value) await router.push('/agent')
  dispatch(type, payload)
}

async function remove(session: any) {
  try {
    await removeSession(session)
  } catch (e) {
    toast(e instanceof Error ? e.message : String(e), 'error')
  }
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
  <div class="space-y-1">
    <button
      v-for="a in actions"
      :key="a.type"
      type="button"
      class="nav-item w-full"
      :class="{ 'nav-item-active': actionActive(a.type) }"
      :title="tr(a.title)"
      @click="go(a.type)"
    >
      <AppIcon :name="a.icon" />
      <span v-if="open" class="truncate">{{ tr(a.title) }}</span>
    </button>
  </div>

  <div v-if="open" class="mt-5">
    <div class="mb-1 flex items-center justify-between pl-3.5 pr-1 text-[11px] font-medium tracking-wider text-ink-faint">
      <span>{{ tr('最近对话') }}</span>
      <button type="button" class="recent-action" :title="tr('搜索对话')" @click="go('search')">
        <AppIcon name="search" class="!text-[15px]" />
      </button>
    </div>
    <button
      v-for="s in sessions"
      :key="s.id"
      type="button"
      class="recent-row"
      :class="{ 'recent-row-active': onAgent && activeSessionId === s.id }"
      @click="go('open', { id: s.id })"
    >
      <span class="status-dot" :class="s.status" />
      <span class="min-w-0 flex-1 truncate text-left">{{ sessionTitle(s) }}</span>
      <span v-if="!deletable(s)" class="spinner" />
      <span
        v-else
        class="recent-action row-delete"
        role="button"
        tabindex="0"
        :title="tr('删除对话')"
        @click.stop="remove(s)"
        @keydown.enter.stop.prevent="remove(s)"
      >
        <AppIcon name="delete" class="!text-[15px]" />
      </span>
    </button>
    <p v-if="!sessions.length" class="px-3.5 py-2 text-xs text-ink-faint">{{ tr('暂无对话') }}</p>
  </div>
</template>

<style scoped>
.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  white-space: nowrap;
  border-radius: 0.375rem;
  border-left: 2px solid transparent;
  padding: 0.5rem 0.875rem;
  font-size: 0.875rem;
  color: var(--color-ink-secondary);
  transition: background-color 0.15s, color 0.15s;
}
.nav-item:hover {
  background-color: var(--color-hover);
}
.nav-item-active {
  border-left-color: var(--color-primary);
  background-color: var(--color-primary-light);
  font-weight: 500;
  color: var(--color-primary);
}
.recent-row {
  display: flex;
  width: 100%;
  align-items: center;
  gap: 0.5rem;
  border-radius: 0.375rem;
  padding: 0.375rem 0.5rem 0.375rem 0.875rem;
  font-size: 0.8125rem;
  color: var(--color-ink-secondary);
}
.recent-row:hover {
  background-color: var(--color-hover);
}
.recent-row-active {
  background-color: var(--color-primary-light);
  color: var(--color-ink);
}
.recent-action {
  display: inline-flex;
  height: 1.375rem;
  width: 1.375rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 0.25rem;
  color: var(--color-ink-muted);
}
.recent-action:hover {
  background-color: var(--color-hover);
  color: var(--color-ink);
}
.row-delete {
  display: none;
}
.recent-row:hover .row-delete,
.row-delete:focus-visible {
  display: inline-flex;
}
.row-delete:hover {
  color: var(--color-danger);
}
.status-dot {
  height: 0.375rem;
  width: 0.375rem;
  flex-shrink: 0;
  border-radius: 9999px;
  background-color: var(--color-ink-faint);
}
.status-dot.completed {
  background-color: var(--color-success);
}
.status-dot.running,
.status-dot.queued {
  background-color: var(--color-warning);
}
.status-dot.failed,
.status-dot.interrupted {
  background-color: var(--color-danger);
}
.spinner {
  height: 0.75rem;
  width: 0.75rem;
  flex-shrink: 0;
  border-radius: 9999px;
  border: 2px solid var(--color-ink-faint);
  border-top-color: transparent;
  animation: agent-nav-spin 0.9s linear infinite;
}
@keyframes agent-nav-spin {
  to {
    transform: rotate(360deg);
  }
}
</style>
