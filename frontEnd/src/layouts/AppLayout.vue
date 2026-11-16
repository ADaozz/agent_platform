<script setup lang="ts">
import { computed, nextTick, onUnmounted, ref, watch } from 'vue'
import { RouterLink, RouterView, useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { tr } from '@/composables/preferences'
import AppIcon from '@/components/AppIcon.vue'
import AgentNav from '@/components/AgentNav.vue'
import BrandMark from '@/components/BrandMark.vue'
import BrandGlyph from '@/components/BrandGlyph.vue'
import TopbarControls from '@/components/TopbarControls.vue'
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
  { path: '/settings/capabilities', title: '平台能力', icon: 'extension' },
  { path: '/settings/usage', title: '用量仪表盘', icon: 'telemetry' },
  { path: '/system/user', title: '用户管理', icon: 'group', permission: 'system:user:list' },
  { path: '/system/role', title: '角色管理', icon: 'shield_person', permission: 'system:role:list' },
  { path: '/system/session', title: '登录设备管理', icon: 'devices', permission: 'system:session:list' },
  { path: '/system/cert/mine', title: '我的证书', icon: 'verified_user', permission: 'system:cert:mine' },
  { path: '/system/cert', title: '证书管理', icon: 'key', permission: 'system:cert:list' },
]
const visibleSettings = computed(() => settingsMenus.filter((m) => !m.permission || auth.hasPerm(m.permission)))

const currentTitle = computed(() => (route.meta.title as string) || '')
const currentGroup = computed(() => (route.meta.group as string) || '')
const settingsActive = computed(() => currentGroup.value === SETTINGS_GROUP)

// 侧栏鼠标悬停展开、移出收起（略作延迟避免划过边缘时闪烁）；展开时占用宽度，主区域整体右移不被遮挡
const sidebarOpen = ref(false)
const railHover = ref(false)

// ≤767px：侧栏改为抽屉，由页头菜单按钮打开，导航后自动收起
const mobileQuery = window.matchMedia('(max-width: 767px)')
const mobile = ref(mobileQuery.matches)
const drawerOpen = ref(false)
const expanded = computed(() => (mobile.value ? drawerOpen.value : sidebarOpen.value))
function onMobileChange(e: MediaQueryListEvent) {
  mobile.value = e.matches
  drawerOpen.value = false
  sidebarOpen.value = false
}
mobileQuery.addEventListener('change', onMobileChange)
/** 抽屉内点了导航项（含最近对话）就收起；设置按钮只负责展开飞出菜单 */
function onNavClick(e: MouseEvent) {
  const target = e.target as HTMLElement
  if (mobile.value && target.closest('.rail-item') && !target.closest('.rail-settings')) drawerOpen.value = false
}
let sidebarTimer: ReturnType<typeof setTimeout> | undefined
function scheduleSidebarClose() {
  clearTimeout(sidebarTimer)
  sidebarTimer = setTimeout(() => {
    sidebarOpen.value = false
  }, 150)
}
function openSidebar() {
  if (mobile.value) return
  clearTimeout(sidebarTimer)
  railHover.value = true
  sidebarOpen.value = true
}
function closeSidebar() {
  if (mobile.value) return
  railHover.value = false
  // 飞出菜单打开时保持侧栏展开，避免移入菜单途中被收起
  if (settingsMenuOpen.value) return
  scheduleSidebarClose()
}

/** 点击弹出飞出菜单（收起/展开侧栏都能用，避免「先悬停再点手风琴」） */
const settingsBtn = ref<HTMLElement | null>(null)
const settingsMenuOpen = ref(false)
const flyoutStyle = ref<Record<string, string>>({})

function placeFlyout() {
  const rect = settingsBtn.value?.getBoundingClientRect()
  if (!rect) return
  const gap = 8
  const maxH = Math.min(360, window.innerHeight - 24)
  // 抽屉里右侧没有空间：贴在按钮上方展开
  if (mobile.value) {
    flyoutStyle.value = {
      bottom: `${window.innerHeight - rect.top + gap}px`,
      left: `${rect.left}px`,
      width: `${rect.width}px`,
      maxHeight: `${Math.min(maxH, rect.top - 24)}px`,
    }
    return
  }
  // 贴按钮右侧，垂直对齐底部；空间不够时改为顶对齐并限制高度
  const bottomSpace = window.innerHeight - rect.top
  if (bottomSpace >= Math.min(maxH, visibleSettings.value.length * 40 + 48)) {
    flyoutStyle.value = {
      top: `${rect.top}px`,
      left: `${rect.right + gap}px`,
      maxHeight: `${maxH}px`,
    }
  } else {
    flyoutStyle.value = {
      bottom: `${window.innerHeight - rect.bottom}px`,
      left: `${rect.right + gap}px`,
      maxHeight: `${maxH}px`,
    }
  }
}

async function toggleSettingsMenu() {
  if (settingsMenuOpen.value) {
    closeSettingsMenu()
    return
  }
  placeFlyout()
  settingsMenuOpen.value = true
  await nextTick()
  placeFlyout()
}

function closeSettingsMenu() {
  if (!settingsMenuOpen.value) return
  settingsMenuOpen.value = false
  // 菜单关了且指针已不在侧栏上时，补一次收起
  if (!railHover.value) scheduleSidebarClose()
}

function onSettingsKeydown(e: KeyboardEvent) {
  if (e.key === 'Escape' && settingsMenuOpen.value) {
    e.preventDefault()
    closeSettingsMenu()
  }
}

watch(
  () => route.fullPath,
  () => {
    closeSettingsMenu()
    drawerOpen.value = false
  },
)

watch(settingsMenuOpen, (open) => {
  if (open) document.addEventListener('keydown', onSettingsKeydown)
  else document.removeEventListener('keydown', onSettingsKeydown)
})

// 侧栏一旦收起，同步关掉飞出菜单，避免菜单悬空留在原位置
watch(expanded, (open) => {
  if (!open && settingsMenuOpen.value) settingsMenuOpen.value = false
})

onUnmounted(() => {
  clearTimeout(sidebarTimer)
  mobileQuery.removeEventListener('change', onMobileChange)
  document.removeEventListener('keydown', onSettingsKeydown)
})

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
    <div v-if="mobile && drawerOpen" class="rail-scrim" aria-hidden="true" @click="drawerOpen = false" />
    <aside
      id="app-rail"
      class="rail"
      :class="{ 'rail-open': expanded, 'rail-drawer': mobile, 'rail-drawer-open': mobile && drawerOpen }"
      :inert="mobile && !drawerOpen"
      @mouseenter="openSidebar"
      @mouseleave="closeSidebar"
      @click="onNavClick"
    >
      <div class="rail-brand">
        <BrandMark v-if="expanded" :size="40" class="rail-logo shrink-0" />
        <BrandGlyph v-else :size="30" />
      </div>

      <nav class="flex min-h-0 flex-1 flex-col">
        <div class="rail-scroll min-h-0 flex-1 overflow-y-auto overflow-x-hidden">
          <AgentNav :open="expanded" />
        </div>

        <!-- 平台设置：点击飞出菜单，收起/展开侧栏交互一致 -->
        <div v-if="visibleSettings.length" class="rail-settings shrink-0">
          <button
            ref="settingsBtn"
            type="button"
            class="rail-item"
            :class="{ 'rail-item-active': settingsActive || settingsMenuOpen }"
            :title="tr(SETTINGS_GROUP)"
            :aria-expanded="settingsMenuOpen"
            aria-haspopup="menu"
            @click.stop="toggleSettingsMenu"
          >
            <AppIcon name="settings" />
            <template v-if="expanded">
              <span class="flex-1 truncate text-left">{{ tr(SETTINGS_GROUP) }}</span>
              <AppIcon name="chevron_right" class="rail-caret" />
            </template>
          </button>
        </div>
      </nav>

      <!-- 操作员铭牌 -->
      <div class="rail-user">
        <div class="rail-avatar" aria-hidden="true">
          {{ (auth.user?.username || '?').charAt(0).toUpperCase() }}
        </div>
        <template v-if="expanded">
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

    <Teleport to="body">
      <template v-if="settingsMenuOpen">
        <div class="rail-flyout-scrim" aria-hidden="true" @click="closeSettingsMenu" />
        <div
          class="rail-flyout"
          role="menu"
          :aria-label="tr(SETTINGS_GROUP)"
          :style="flyoutStyle"
          @click.stop
        >
          <div class="rail-flyout-head">{{ tr(SETTINGS_GROUP) }}</div>
          <RouterLink
            v-for="m in visibleSettings"
            :key="m.path"
            :to="m.path"
            role="menuitem"
            class="rail-flyout-item"
            :class="{ 'rail-flyout-item-active': isMenuActive(m.path) }"
            @click="closeSettingsMenu"
          >
            <AppIcon :name="m.icon" class="!text-[17px]" />
            <span class="min-w-0 flex-1 truncate">{{ tr(m.title) }}</span>
          </RouterLink>
        </div>
      </template>
    </Teleport>

    <!-- 主区域 -->
    <div class="flex min-h-0 min-w-0 flex-1 flex-col">
      <header class="topbar">
        <div class="flex min-w-0 items-center gap-3">
          <button
            v-if="mobile"
            type="button"
            class="topbar-menu"
            :aria-label="tr('打开导航')"
            aria-controls="app-rail"
            :aria-expanded="drawerOpen"
            @click="drawerOpen = true"
          >
            <AppIcon name="menu" class="!text-[20px]" />
          </button>
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
        <TopbarControls />
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
  width: 12rem;
}
.rail-brand {
  display: flex;
  height: 3.5rem;
  flex-shrink: 0;
  align-items: center;
  padding: 0 1.0625rem;
}
.rail-logo {
  animation: rail-logo-in 0.22s var(--ease-out);
}
@keyframes rail-logo-in {
  from { opacity: 0; }
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
.rail-flyout-scrim {
  position: fixed;
  inset: 0;
  z-index: 40;
}
.rail-flyout {
  position: fixed;
  z-index: 41;
  display: flex;
  min-width: 11.5rem;
  max-width: 16rem;
  flex-direction: column;
  gap: 2px;
  overflow-y: auto;
  padding: 0.375rem;
  border: 1px solid var(--chrome-line);
  border-radius: 12px;
  background-color: var(--chrome-raised);
  box-shadow: var(--shadow-panel);
  color: var(--chrome-ink-2);
}
.rail-flyout-head {
  padding: 0.4rem 0.75rem 0.35rem;
  font-size: 11px;
  letter-spacing: 0.06em;
  color: var(--chrome-ink-3);
}
.rail-flyout-item {
  display: flex;
  height: 2.25rem;
  align-items: center;
  gap: 0.625rem;
  padding: 0 0.75rem;
  border-radius: 8px;
  font-size: 13px;
  color: var(--chrome-ink-2);
  transition:
    background-color 0.16s,
    color 0.16s;
}
.rail-flyout-item:hover,
.rail-flyout-item:focus-visible {
  background-color: var(--chrome-glass);
  color: var(--chrome-ink);
  outline: none;
}
.rail-flyout-item-active {
  background-color: var(--chrome-glass);
  color: var(--chrome-ink);
  font-weight: 500;
}
.rail-flyout-item-active > .app-icon:first-child {
  color: var(--chrome-signal);
}

/* 导航项：圆角胶囊；悬停浮出玻璃底，左侧亮起信号橙标记 */
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
  inset: 9px auto 9px 0;
  width: 3px;
  background: var(--color-signal);
  pointer-events: none;
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
  opacity: 0.35;
  transform: none;
}
.rail-item.rail-item-active::before,
.rail-item.recent-row-active::before {
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
@media (max-width: 767px) {
  .topbar {
    padding: 0 0.875rem;
  }
  .topbar-path > :not(.topbar-current) {
    display: none;
  }
}

/* ≤767px：侧栏为抽屉，覆盖在内容之上 */
.rail-scrim {
  position: fixed;
  inset: 0;
  z-index: 44;
  background: rgb(0 0 0 / 0.45);
  animation: rail-scrim-in 0.2s var(--ease-out);
}
@keyframes rail-scrim-in {
  from { opacity: 0; }
}
.rail.rail-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 45;
  width: min(17rem, 84vw);
  height: 100dvh;
  padding-bottom: env(safe-area-inset-bottom);
  transform: translateX(-100%);
  transition: transform 0.24s var(--ease-out), box-shadow 0.24s;
}
.rail.rail-drawer-open {
  transform: none;
  box-shadow: 12px 0 32px rgb(0 0 0 / 0.28);
}
.topbar-menu {
  display: inline-flex;
  height: 2.5rem;
  width: 2.5rem;
  margin-left: -0.5rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: var(--color-ink-muted);
}
.topbar-menu:hover,
.topbar-menu:focus-visible {
  background-color: var(--color-line);
  color: var(--color-ink);
  outline: none;
}
@media (max-width: 767px) {
  .rail-flyout-scrim {
    z-index: 46;
  }
  .rail-flyout {
    z-index: 47;
    min-width: 0;
    max-width: none;
  }
}
@media (prefers-reduced-motion: reduce) {
  .rail.rail-drawer {
    transition: none;
  }
}

/* 触屏：导航项保持控制台密度，但把命中区加到 44px */
@media (pointer: coarse) {
  .rail-item,
  .rail-flyout-item {
    height: 2.75rem;
  }
  .rail-logout {
    height: 2.75rem;
    width: 2.75rem;
  }
}


.page-canvas {
  padding: 1.75rem 2rem 2.5rem;
}
@media (max-width: 767px) {
  .page-canvas {
    padding: 1.25rem 1rem 2rem;
  }
}
</style>
