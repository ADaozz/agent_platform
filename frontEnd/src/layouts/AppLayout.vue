<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { locale, theme, toggleLocale, toggleTheme, tr } from '@/composables/preferences'
import AppIcon from '@/components/AppIcon.vue'
import AgentNav from '@/components/AgentNav.vue'
import BrandMark from '@/components/BrandMark.vue'
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
  { path: '/settings/models', title: '模型配置', icon: 'module' },
  { path: '/system/user', title: '用户管理', icon: 'access', permission: 'system:user:list' },
  { path: '/system/role', title: '角色管理', icon: 'route', permission: 'system:role:list' },
  { path: '/system/session', title: '登录设备管理', icon: 'satellite', permission: 'system:session:list' },
  { path: '/system/cert/mine', title: '我的证书', icon: 'scan', permission: 'system:cert:mine' },
  { path: '/system/cert', title: '证书管理', icon: 'beacon', permission: 'system:cert:list' },
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

// 页头的本地时钟读数（分钟精度）
const clock = ref('')
const zone = (() => {
  const offset = -new Date().getTimezoneOffset()
  const hours = Math.trunc(offset / 60)
  const minutes = Math.abs(offset % 60)
  return `UTC${offset >= 0 ? '+' : '-'}${Math.abs(hours)}${minutes ? ':' + String(minutes).padStart(2, '0') : ''}`
})()
function tick() {
  const now = new Date()
  clock.value = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}`
}
let clockTimer: ReturnType<typeof setInterval> | undefined
onMounted(() => {
  tick()
  clockTimer = setInterval(tick, 15000)
})
onUnmounted(() => clearInterval(clockTimer))

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
  <div class="shell flex h-full min-h-0">
    <!-- 侧栏：跟随明暗主题 -->
    <aside class="rail" :class="{ 'rail-open': sidebarOpen }" @mouseenter="openSidebar" @mouseleave="closeSidebar">
      <div class="rail-brand">
        <BrandMark :size="30" class="shrink-0" />
        <div v-if="sidebarOpen" class="rail-wordmark">
          <div class="rail-wordmark-name">DEEP AGENT</div>
          <span class="tri-bar rail-tri" aria-hidden="true"></span>
        </div>
      </div>

      <nav class="flex min-h-0 flex-1 flex-col">
        <div class="rail-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <AgentNav :open="sidebarOpen" />
        </div>

        <!-- 平台设置固定在导航最底部 -->
        <div v-if="visibleSettings.length" class="rail-settings shrink-0">
          <button
            type="button"
            class="rail-item"
            :class="{ 'rail-item-active': settingsActive && !(sidebarOpen && settingsOpen) }"
            :title="tr(SETTINGS_GROUP)"
            :aria-expanded="settingsOpen"
            @click="settingsOpen = !settingsOpen"
          >
            <AppIcon name="orbit" />
            <template v-if="sidebarOpen">
              <span class="flex-1 truncate text-left">{{ tr(SETTINGS_GROUP) }}</span>
              <AppIcon name="expand_more" class="rail-caret" :class="{ 'rotate-180': settingsOpen }" />
            </template>
          </button>
          <div v-show="sidebarOpen && settingsOpen" class="rail-submenu">
            <RouterLink
              v-for="m in visibleSettings"
              :key="m.path"
              :to="m.path"
              :title="tr(m.title)"
              class="rail-item rail-subitem"
              :class="{ 'rail-item-active': isMenuActive(m.path) }"
            >
              <AppIcon :name="m.icon" class="!text-[17px]" />
              <span class="flex-1 truncate">{{ tr(m.title) }}</span>
            </RouterLink>
          </div>
        </div>
      </nav>

      <!-- 操作员铭牌 -->
      <div class="rail-user">
        <div class="rail-avatar" aria-hidden="true">
          {{ (auth.user?.username || '?').charAt(0).toUpperCase() }}
        </div>
        <template v-if="sidebarOpen">
          <div class="min-w-0 flex-1 whitespace-nowrap leading-tight">
            <div class="truncate text-[13px] font-medium text-[var(--chrome-ink)]">{{ auth.user?.username }}</div>
            <div class="rail-role">{{ tr(isAdmin ? '管理员' : '普通用户') }}</div>
          </div>
          <button class="rail-logout" :title="tr('退出登录')" :aria-label="tr('退出登录')" @click="handleLogout">
            <AppIcon name="logout" class="!text-[17px]" />
          </button>
        </template>
      </div>
    </aside>

    <!-- 主区域 -->
    <div class="flex min-h-0 min-w-0 flex-1 flex-col">
      <header class="topbar">
        <div class="flex min-w-0 items-center gap-3">
          <div class="topbar-path">
            <span class="whitespace-nowrap">DEEP AGENT</span>
            <template v-if="currentGroup">
              <span class="topbar-sep" aria-hidden="true">/</span>
              <span class="whitespace-nowrap">{{ tr(currentGroup) }}</span>
            </template>
            <span class="topbar-sep" aria-hidden="true">/</span>
            <span class="topbar-current truncate">{{ tr(currentTitle) }}</span>
          </div>
        </div>
        <div class="flex shrink-0 items-center gap-1.5">
          <div class="topbar-clock" :title="zone">
            <span class="topbar-clock-time">{{ clock }}</span>
            <span>{{ zone }}</span>
          </div>
          <button
            type="button"
            class="topbar-toggle topbar-locale"
            :title="tr('切换语言')"
            :aria-label="tr('切换语言')"
            @click="toggleLocale"
          >
            {{ locale === 'zh' ? '中' : 'EN' }}
          </button>
          <button
            type="button"
            class="topbar-toggle"
            :title="tr(theme === 'dark' ? '切换为白天模式' : '切换为黑夜模式')"
            :aria-label="tr(theme === 'dark' ? '切换为白天模式' : '切换为黑夜模式')"
            :aria-pressed="theme === 'dark'"
            @click="toggleTheme"
          >
            <AppIcon :name="theme === 'dark' ? 'dark_mode' : 'light_mode'" class="!text-[17px]" />
          </button>
        </div>
      </header>
      <main class="min-h-0 flex-1 overflow-y-auto" :class="route.path === '/agent' ? 'p-0' : 'page-canvas dot-grid'">
        <RouterView />
      </main>
    </div>
    <SessionDeleteConfirm />
  </div>
</template>

<!-- 不加 scoped：.rail-* 同时供侧栏内的 AgentNav 使用 -->
<style>
/* ───────── 侧栏 ───────── */
/* 白天模式下侧栏为浅色，品牌标识反相以保持对比 */
[data-theme='light'] .rail {
  --mark-tile: #181818;
  --mark-ink: #f5eddc;
}
.rail {
  display: flex;
  width: 4rem;
  flex-shrink: 0;
  flex-direction: column;
  overflow: hidden;
  background-color: var(--chrome-bg);
  border-right: 1px solid var(--chrome-line);
  color: var(--chrome-ink-2);
  transition: width 0.22s var(--ease-out);
}
.rail-open {
  width: 15.5rem;
}
.rail-brand {
  display: flex;
  height: 3.5rem;
  flex-shrink: 0;
  align-items: center;
  gap: 0.75rem;
  padding: 0 1.0625rem;
}
.rail-wordmark {
  min-width: 0;
  white-space: nowrap;
}
.rail-wordmark-name {
  font-family: var(--font-display);
  font-size: 20px;
  font-weight: 700;
  line-height: 1;
  letter-spacing: 0.07em;
  color: var(--chrome-ink);
}
.rail-tri {
  width: 100%;
  height: 3px;
  margin-top: 6px;
}
.rail-scroll {
  padding: 0.5rem 0 0.75rem;
  scrollbar-color: var(--chrome-line) transparent;
}
.rail-settings {
  margin: 0 0.5rem;
  border-top: 1px solid var(--chrome-line);
  padding: 0.5rem 0;
}
.rail-settings .rail-item {
  width: 100%;
  margin-left: 0;
  margin-right: 0;
}

/* 导航项：圆角胶囊；悬停浮出玻璃底，左侧亮起红黄绿标记 */
.rail-item {
  position: relative;
  display: flex;
  width: calc(100% - 1rem);
  height: 2.375rem;
  margin: 1px 0.5rem;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.625rem 0 0.875rem;
  border-radius: 10px;
  white-space: nowrap;
  font-size: 13.5px;
  color: var(--chrome-ink-2);
  transition:
    background-color 0.16s,
    color 0.16s;
}
.rail-item::before {
  content: '';
  position: absolute;
  inset: 9px auto 9px 2px;
  width: 6px;
  background: var(--tricolor-h);
  opacity: 0;
  transform: scaleY(0.35);
  transition:
    opacity 0.16s var(--ease-out),
    transform 0.2s var(--ease-out);
}
.rail-item:hover,
.rail-item:focus-visible {
  background-color: var(--chrome-glass);
  color: var(--chrome-ink);
  outline: none;
}
.rail-item:focus-visible {
  box-shadow: inset 0 0 0 1.5px var(--chrome-signal);
}
.rail-item:hover::before,
.rail-item:focus-visible::before {
  opacity: 1;
  transform: none;
}
.rail-item-active {
  background-color: var(--chrome-glass);
  color: var(--chrome-ink);
  font-weight: 500;
}
.rail-item-active > .app-icon:first-child {
  color: var(--chrome-signal);
}
.rail-caret {
  font-size: 15px !important;
  color: var(--chrome-ink-3);
  transition: transform 0.2s var(--ease-out);
}
.rail-submenu {
  padding-bottom: 0.25rem;
}
.rail-subitem {
  height: 2.125rem;
  padding-left: 1.75rem;
  font-size: 13px;
}

.rail-user {
  display: flex;
  flex-shrink: 0;
  align-items: center;
  gap: 0.75rem;
  margin: 0 0.5rem;
  padding: 0.75rem 0.5rem;
  border-top: 1px solid var(--chrome-line);
}
.rail-avatar {
  display: flex;
  height: 2rem;
  width: 2rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: var(--chrome-raised);
  box-shadow: inset 0 0 0 1px var(--chrome-line);
  font-family: var(--font-display);
  font-size: 16px;
  font-weight: 700;
  color: var(--chrome-signal);
}
.rail-role {
  margin-top: 3px;
  font-size: 11px;
  color: var(--chrome-ink-3);
}
.rail-logout {
  display: flex;
  height: 1.875rem;
  width: 1.875rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--chrome-ink-3);
  transition:
    background-color 0.16s,
    color 0.16s;
}
.rail-logout:hover {
  background-color: var(--chrome-glass);
  color: var(--color-danger);
}

/* ───────── 页头 ───────── */
.topbar {
  display: flex;
  height: 3.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding: 0 1.5rem;
  border-bottom: 1px solid var(--color-line);
  background-color: var(--color-page);
}
.topbar-toggle {
  display: inline-flex;
  height: 2rem;
  width: 2rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-ink-muted);
  transition:
    background-color 0.16s,
    color 0.16s;
}
.topbar-toggle:hover {
  background-color: var(--glass-strong);
  color: var(--color-ink);
}
.topbar-path {
  display: flex;
  min-width: 0;
  align-items: center;
  gap: 0.5rem;
  font-size: 12.5px;
  letter-spacing: 0.04em;
  color: var(--color-ink-muted);
}
.topbar-sep {
  color: var(--color-ink-faint);
}
.topbar-current {
  font-weight: 600;
  color: var(--color-ink);
}
.topbar-clock {
  display: flex;
  align-items: baseline;
  gap: 0.5rem;
  margin-right: 0.375rem;
  padding-right: 0.875rem;
  border-right: 1px solid var(--color-line);
  font-family: var(--font-mono);
  font-size: 10px;
  letter-spacing: 0.12em;
  color: var(--color-ink-faint);
}
.topbar-clock-time {
  font-size: 13px;
  letter-spacing: 0.06em;
  font-variant-numeric: tabular-nums;
  color: var(--color-ink-secondary);
}
@media (max-width: 720px) {
  .topbar {
    padding: 0 0.875rem;
  }
  .topbar-clock {
    display: none;
  }
  .topbar-path > :not(.topbar-current) {
    display: none;
  }
}

.topbar-locale {
  font-size: 12.5px;
  font-weight: 600;
}

.page-canvas {
  padding: 1.75rem 2rem 2.5rem;
}
@media (max-width: 720px) {
  .page-canvas {
    padding: 1.25rem 1rem 2rem;
  }
}
</style>
