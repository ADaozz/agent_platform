import { reactive } from 'vue'

export type ToastType = 'success' | 'error' | 'info'

export interface ToastItem {
  id: number
  type: ToastType
  message: string
}

let seed = 0

export const toasts = reactive<ToastItem[]>([])

export function toast(message: string, type: ToastType = 'info', duration = 3000) {
  const id = ++seed
  toasts.push({ id, type, message })
  window.setTimeout(() => {
    const idx = toasts.findIndex((t) => t.id === id)
    if (idx >= 0) toasts.splice(idx, 1)
  }, duration)
}

toast.success = (message: string) => toast(message, 'success')
toast.error = (message: string) => toast(message, 'error', 4000)
toast.info = (message: string) => toast(message, 'info')
