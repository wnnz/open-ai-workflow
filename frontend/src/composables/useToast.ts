import { readonly, ref, toValue, watch, type MaybeRefOrGetter } from 'vue'

export type ToastTone = 'success' | 'error' | 'info'

export interface ToastMessage {
  id: number
  message: string
  tone: ToastTone
}

const items = ref<ToastMessage[]>([])
const timers = new Map<number, ReturnType<typeof setTimeout>>()
let nextId = 1

export const toastMessages = readonly(items)

function scheduleDismiss(id: number, duration: number) {
  const current = timers.get(id)
  if (current) clearTimeout(current)
  if (duration <= 0) return
  timers.set(id, setTimeout(() => dismissToast(id), duration))
}

export function dismissToast(id: number) {
  const timer = timers.get(id)
  if (timer) clearTimeout(timer)
  timers.delete(id)
  items.value = items.value.filter(item => item.id !== id)
}

export function clearToasts() {
  timers.forEach(timer => clearTimeout(timer))
  timers.clear()
  items.value = []
}

export function showToast(message: string, tone: ToastTone = 'info', duration?: number) {
  const normalized = message.trim()
  if (!normalized) return 0
  const timeout = duration ?? (tone === 'error' ? 7000 : tone === 'success' ? 4000 : 5000)
  const existing = items.value.find(item => item.message === normalized && item.tone === tone)
  if (existing) {
    scheduleDismiss(existing.id, timeout)
    return existing.id
  }
  const id = nextId++
  items.value = [...items.value, { id, message: normalized, tone }]
  scheduleDismiss(id, timeout)
  return id
}

export function useToast() {
  return {
    show: showToast,
    success: (message: string, duration?: number) => showToast(message, 'success', duration),
    error: (message: string, duration?: number) => showToast(message, 'error', duration),
    info: (message: string, duration?: number) => showToast(message, 'info', duration),
    dismiss: dismissToast,
  }
}

export function useToastMessage(source: MaybeRefOrGetter<string | null | undefined>, tone: ToastTone = 'info') {
  watch(() => toValue(source), message => {
    if (message) showToast(message, tone)
  }, { immediate: true })
}
