<script setup lang="ts">
import { computed, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { locale, theme, toggleLocale, toggleTheme, tr } from '@/composables/preferences'
import AppIcon from '@/components/AppIcon.vue'
import AgentNav from '@/components/AgentNav.vue'
import SessionDeleteConfirm from '@/components/SessionDeleteConfirm.vue'
import type { IconName } from '@/icons'

const auth = useAuthStore()
const route = useRoute()
const router = useRouter()

interface MenuItem {
  path: string
  title: string
  icon: IconName
  permission?: string
}

const SETTINGS_GROUP = '平台设置'
const settingsMenus: MenuItem[] = [
  { path: '/settings/models', title: '模型配置', icon: 'memory' },
  { path: '/system/user', title: '用户管理', icon: 'manage_accounts', permission: 'system:user:list' },
  { path: '/system/role', title: '角色管理', icon: 'shield_person', permission: 'system:role:list' },
  { path: '/system/session', title: '登录设备管理', icon: 'devices', permission: 'system:session:list' },
  { path: '/system/cert/mine', title: '我的证书', icon: 'verified_user', permission: 'system:cert:mine' },
  { path: '/system/cert', title: '证书管理', icon: 'shield_person', permission: 'system:cert:list' },
]
const visibleSettings = computed(() => settingsMenus.filter((m) => !m.permission || auth.hasPerm(m.permission)))

const currentTitle = computed(() => (route.meta.title as string) || '')
const currentGroup = computed(() => (route.meta.group as string) || '')
const settingsActive = computed(() => currentGroup.value === SETTINGS_GROUP)

// 侧栏鼠标悬停展开、移出收起（略作延迟避免划过边缘时闪烁）；展开时占用宽度，主区域整体右移不被遮挡
const sidebarOpen = ref(false)
let sidebarTimer: ReturnType<typeof setTimeout> | undefined
function openSidebar() {
  clearTimeout(sidebarTimer)
  sidebarOpen.value = true
}
function closeSidebar() {
  clearTimeout(sidebarTimer)
  sidebarTimer = setTimeout(() => (sidebarOpen.value = false), 150)
}
onUnmounted(() => clearTimeout(sidebarTimer))

// 「平台设置」点击展开/收起；当前页面属于该分组时默认展开
const settingsOpen = ref(settingsActive.value)

/** 最长路径优先，避免 /system/cert/mine 同时高亮 /system/cert */
function isMenuActive(path: string) {
  const matched = visibleSettings.value
    .filter((m) => route.path === m.path || route.path.startsWith(`${m.path}/`))
    .sort((a, b) => b.path.length - a.path.length)[0]
  return matched?.path === path
}

const isAdmin = computed(() => (auth.user?.roles ?? []).some((r) => r.label === 'admin'))

function handleLogout() {
  auth.logout().then(() => router.push('/login'))
}
</script>

<template>
  <div class="flex h-full min-h-0">
    <aside
      class="flex shrink-0 flex-col overflow-hidden border-r border-line bg-card transition-[width] duration-200"
      :class="sidebarOpen ? 'w-60' : 'w-16'"
      @mouseenter="openSidebar"
      @mouseleave="closeSidebar"
    >
      <div class="flex h-14 shrink-0 items-center gap-2.5 border-b border-line px-4">
        <img src="/deep-agent-icon.svg" alt="Deep Agent" class="h-8 w-8 shrink-0 rounded-md" />
        <div v-if="sidebarOpen" class="min-w-0 whitespace-nowrap leading-tight">
          <div class="text-sm font-semibold text-ink">Agent Platform</div>
          <div class="text-[11px] text-ink-faint">Agent Workspace</div>
        </div>
      </div>

      <nav class="flex min-h-0 flex-1 flex-col p-2">
        <div class="min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <AgentNav :open="sidebarOpen" />
        </div>

        <!-- 平台设置固定在导航最底部 -->
        <div v-if="visibleSettings.length" class="mt-2 shrink-0 space-y-1 border-t border-line pt-2">
          <button
            type="button"
            class="menu-item w-full"
            :class="{ 'menu-item-active': settingsActive && !(sidebarOpen && settingsOpen) }"
            :title="tr(SETTINGS_GROUP)"
            :aria-expanded="settingsOpen"
            @click="settingsOpen = !settingsOpen"
          >
            <AppIcon name="settings" />
            <template v-if="sidebarOpen">
              <span class="flex-1 truncate text-left">{{ tr(SETTINGS_GROUP) }}</span>
              <AppIcon name="expand_more" class="!text-[18px] transition-transform" :class="{ 'rotate-180': settingsOpen }" />
            </template>
          </button>
          <div v-show="sidebarOpen && settingsOpen" class="submenu space-y-1">
            <RouterLink
              v-for="m in visibleSettings"
              :key="m.path"
              :to="m.path"
              :title="tr(m.title)"
              class="menu-item menu-subitem"
              :class="{ 'menu-item-active': isMenuActive(m.path) }"
            >
              <AppIcon :name="m.icon" class="!text-[18px]" />
              <span class="truncate">{{ tr(m.title) }}</span>
            </RouterLink>
          </div>
        </div>
      </nav>

      <div class="shrink-0 border-t border-line px-4 py-3">
        <div class="flex items-center gap-2.5">
          <div class="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary-light text-sm font-semibold text-primary">
            {{ (auth.user?.username || '?').charAt(0).toUpperCase() }}
          </div>
          <template v-if="sidebarOpen">
            <div class="min-w-0 flex-1 whitespace-nowrap leading-tight">
              <div class="truncate text-sm font-medium text-ink">{{ auth.user?.username }}</div>
              <div class="truncate text-[11px] text-ink-faint">{{ tr(isAdmin ? '管理员' : '普通用户') }}</div>
            </div>
            <button
              class="flex h-7 w-7 shrink-0 items-center justify-center rounded text-ink-muted transition-colors hover:bg-hover hover:text-danger"
              :title="tr('退出登录')"
              @click="handleLogout"
            >
              <AppIcon name="logout" class="!text-[18px]" />
            </button>
          </template>
        </div>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="flex min-h-0 min-w-0 flex-1 flex-col">
      <header class="flex h-14 shrink-0 items-center justify-between border-b border-line bg-card px-6">
        <div class="flex min-w-0 items-center gap-2 text-sm text-ink-muted">
          <span class="whitespace-nowrap">Agent Platform</span>
          <template v-if="currentGroup">
            <AppIcon name="chevron_right" class="!text-[16px]" />
            <span class="whitespace-nowrap">{{ tr(currentGroup) }}</span>
          </template>
          <AppIcon name="chevron_right" class="!text-[16px]" />
          <span class="truncate font-medium text-ink">{{ tr(currentTitle) }}</span>
        </div>
        <div class="flex shrink-0 items-center gap-1">
          <button type="button" class="header-toggle" :title="tr('切换语言')" @click="toggleLocale">
            <AppIcon name="translate" class="!text-[18px]" />
            <span class="text-xs">{{ locale === 'zh' ? '中文' : 'EN' }}</span>
          </button>
          <button
            type="button"
            class="header-toggle"
            :title="tr(theme === 'dark' ? '切换为白天模式' : '切换为黑夜模式')"
            :aria-pressed="theme === 'dark'"
            @click="toggleTheme"
          >
            <AppIcon :name="theme === 'dark' ? 'light_mode' : 'dark_mode'" class="!text-[18px]" />
          </button>
        </div>
      </header>
      <main class="min-h-0 flex-1 overflow-y-auto" :class="route.path === '/agent' ? 'p-0' : 'p-6'">
        <RouterView />
      </main>
    </div>
    <SessionDeleteConfirm />
  </div>
</template>

<style scoped>
.menu-item {
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
.menu-item:hover {
  background-color: var(--color-hover);
}
/* 二级菜单：整体右缩进，并用左侧细线标出所属分组 */
.submenu {
  margin-left: 1.5rem;
  padding-left: 0.5rem;
  border-left: 1px solid var(--color-line);
}
.menu-subitem {
  padding-top: 0.375rem;
  padding-bottom: 0.375rem;
  padding-left: 0.75rem;
  font-size: 0.8125rem;
}
.menu-item-active {
  border-left-color: var(--color-primary);
  background-color: var(--color-primary-light);
  font-weight: 500;
  color: var(--color-primary);
}
.header-toggle {
  display: inline-flex;
  height: 2rem;
  align-items: center;
  gap: 0.25rem;
  border-radius: 0.375rem;
  padding: 0 0.5rem;
  color: var(--color-ink-muted);
  transition: background-color 0.15s, color 0.15s;
}
.header-toggle:hover {
  background-color: var(--color-hover);
  color: var(--color-ink);
}
</style>
