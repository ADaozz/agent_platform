<script setup lang="ts">
import { tr } from '@/composables/preferences'
import AppIcon from '@/components/AppIcon.vue'
import { nextTick, onBeforeUnmount, ref, useId, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    open: boolean
    title: string
    width?: string
    /** 垂直居中；默认偏上，便于长表单滚动 */
    centered?: boolean
    /** 面板底色：card 默认卡片色；page 与页面米色/主题底色一致 */
    surface?: 'card' | 'page'
  }>(),
  {
    centered: false,
    surface: 'card',
  },
)

const emit = defineEmits<{ close: [] }>()

const titleId = useId()
const panel = ref<HTMLElement | null>(null)
let restoreFocus: HTMLElement | null = null
let previousOverflow = ''

const FOCUSABLE =
  'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function focusable(): HTMLElement[] {
  if (!panel.value) return []
  return Array.from(panel.value.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
    (el) => el.getClientRects().length > 0 && el.getAttribute('aria-hidden') !== 'true',
  )
}

/** Esc 关闭，Tab / Shift+Tab 在弹窗内循环，焦点不落到背景页面 */
function onKeydown(event: KeyboardEvent) {
  if (!props.open) return
  if (event.key === 'Escape') {
    // Let the native picker consume Escape before closing its containing dialog.
    if (CSS.supports('selector(select:open)') && panel.value?.querySelector('select:open')) return
    event.preventDefault()
    emit('close')
    return
  }
  if (event.key !== 'Tab') return
  const items = focusable()
  if (!items.length) {
    event.preventDefault()
    panel.value?.focus()
    return
  }
  const first = items[0]!
  const last = items[items.length - 1]!
  const active = document.activeElement as HTMLElement | null
  // A step change can remove the focused element; keep the next Tab in the modal.
  if (!panel.value?.contains(active)) {
    event.preventDefault()
    ;(event.shiftKey ? last : first).focus()
    return
  }
  if (event.shiftKey && (active === first || !panel.value?.contains(active))) {
    event.preventDefault()
    last.focus()
  } else if (!event.shiftKey && active === last) {
    event.preventDefault()
    first.focus()
  }
}

watch(
  () => props.open,
  async (open) => {
    if (open) {
      restoreFocus = document.activeElement as HTMLElement | null
      previousOverflow = document.body.style.overflow
      document.body.style.overflow = 'hidden'
      document.addEventListener('keydown', onKeydown)
      await nextTick()
      const firstField = panel.value?.querySelector<HTMLElement>(
        '[autofocus], input:not([disabled]), select:not([disabled]), textarea:not([disabled])',
      )
      ;(firstField ?? panel.value)?.focus()
    } else {
      document.removeEventListener('keydown', onKeydown)
      document.body.style.overflow = previousOverflow
      const target = restoreFocus
      restoreFocus = null
      await nextTick()
      target?.focus()
    }
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  if (props.open) document.body.style.overflow = previousOverflow
})
</script>

<template>
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="open"
        class="modal-scrim"
        :class="{ 'modal-scrim--center': centered }"
        @mousedown.self="emit('close')"
      >
        <div
          ref="panel"
          class="modal-panel"
          :class="{ 'modal-panel--page': surface === 'page' }"
          role="dialog"
          aria-modal="true"
          :aria-labelledby="titleId"
          tabindex="-1"
          :style="{ maxWidth: width || '480px' }"
        >
          <div class="modal-head">
            <div class="min-w-0 flex-1">
              <h3 :id="titleId" class="modal-title">{{ title }}</h3>
              <span class="tri-bar modal-tri" aria-hidden="true"></span>
            </div>
            <button type="button" class="modal-close" :aria-label="tr('关闭')" @click="emit('close')">
              <AppIcon name="close" class="!text-[17px]" />
            </button>
          </div>
          <div class="px-6 py-5">
            <slot />
          </div>
          <div v-if="$slots.footer" class="modal-foot">
            <slot name="footer" />
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<style scoped>
.modal-scrim {
  position: fixed;
  inset: 0;
  z-index: 50;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  overflow-y: auto;
  padding: 10vh 1.5rem 1.5rem;
  background-color: var(--overlay);
  backdrop-filter: blur(6px) saturate(0.9);
}
.modal-scrim--center {
  align-items: center;
  padding: 1.5rem;
}
.modal-panel {
  position: relative;
  width: 100%;
  border: 1px solid var(--color-line);
  border-radius: 16px;
  overflow: hidden;
  background-color: var(--color-card);
  box-shadow: var(--shadow-panel);
}
.modal-panel--page {
  background-color: var(--color-page);
}
.modal-head {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1.125rem 1rem 0.25rem 1.5rem;
}
.modal-tri {
  width: 72px;
  height: 3px;
  margin-top: 0.5rem;
}
.modal-title {
  font-size: 16px;
  font-weight: 700;
  letter-spacing: 0.02em;
  color: var(--color-ink);
}
.modal-close {
  display: flex;
  height: 1.75rem;
  width: 1.75rem;
  flex-shrink: 0;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  color: var(--color-ink-muted);
  transition:
    background-color 0.16s,
    color 0.16s;
}
.modal-close:hover {
  background-color: var(--glass-strong);
  color: var(--color-ink);
}
.modal-foot {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  border-top: 1px solid var(--color-line);
  background-color: var(--glass);
}

@media (max-width: 767px) {
  .modal-close {
    height: 2.75rem;
    width: 2.75rem;
  }
}

.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.18s var(--ease-out);
}
.modal-enter-active .modal-panel,
.modal-leave-active .modal-panel {
  transition: transform 0.2s var(--ease-out);
}
.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}
.modal-enter-from .modal-panel,
.modal-leave-to .modal-panel {
  transform: translateY(8px);
}
</style>
