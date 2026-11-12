<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { locale, theme, toggleLocale, toggleTheme, tr } from '@/composables/preferences'
import AppIcon from '@/components/AppIcon.vue'

// 本地时钟读数（分钟精度）
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
</script>

<template>
  <!-- 页头右侧：本地时钟、语言与明暗切换；平台页头与登录页共用 -->
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
</template>

<style scoped>
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
.topbar-locale {
  font-size: 12.5px;
  font-weight: 600;
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
  .topbar-clock {
    display: none;
  }
}
</style>
