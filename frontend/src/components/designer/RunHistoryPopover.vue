<script setup lang="ts">
import { Activity, ChevronRight, RefreshCw, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

withDefaults(defineProps<{ open: boolean; runs: any[]; embedded?: boolean; selectedRunId?: string }>(), { embedded: false, selectedRunId: '' })
const emit = defineEmits<{ close: []; refresh: []; replay: [run: any] }>()
const { t, te } = useI18n()

function statusClass(status: string) {
  if (status === 'succeeded') return 'bg-emerald-500'
  if (status === 'failed') return 'bg-red-500'
  if (status === 'running') return 'bg-blue-500'
  if (status === 'waiting' || status === 'pending' || status === 'cancelling') return 'bg-amber-500'
  return 'bg-slate-400'
}

function statusTone(status: string) {
  if (status === 'succeeded') return 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300'
  if (status === 'failed') return 'bg-red-50 text-red-700 dark:bg-red-950/40 dark:text-red-300'
  if (status === 'running') return 'bg-blue-50 text-blue-700 dark:bg-blue-950/40 dark:text-blue-300'
  if (status === 'waiting' || status === 'pending' || status === 'cancelling') return 'bg-amber-50 text-amber-700 dark:bg-amber-950/40 dark:text-amber-300'
  return 'bg-[var(--panel-subtle)] text-[var(--muted)]'
}

function statusLabel(status: string) {
  const key = `designer.runStatus.${status}`
  return te(key) ? t(key) : status
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString([], { year: 'numeric', month: '2-digit', day: '2-digit' })
}

function formatTime(value: string) {
  return new Date(value).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>

<template>
  <div
    v-if="open"
    class="surface overflow-hidden"
    :class="embedded ? 'relative w-full rounded-lg' : 'absolute right-0 top-10 z-[60] w-80 rounded-xl shadow-2xl'"
  >
    <header class="flex items-center gap-3 border-b border-[var(--border)]" :class="embedded ? 'min-h-16 px-5 py-3' : 'h-12 px-4'">
      <span v-if="embedded" class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[var(--primary-soft)] text-[var(--primary)]"><Activity :size="16" /></span>
      <Activity v-else :size="15" class="text-[var(--primary)]" />
      <div class="min-w-0">
        <div class="flex items-center gap-2">
          <h2 class="text-sm font-semibold">{{ t('designer.runHistory') }}</h2>
          <span v-if="embedded" class="rounded bg-[var(--panel-subtle)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--muted)]">{{ runs.length }}</span>
        </div>
        <p v-if="embedded" class="muted mt-0.5 text-[10px]">{{ t('designer.logsHint') }}</p>
      </div>
      <button type="button" class="icon-button ml-auto" :title="t('common.refresh')" :aria-label="t('common.refresh')" @click="emit('refresh')"><RefreshCw :size="14" /></button>
      <button v-if="!embedded" type="button" class="icon-button" :aria-label="$t('common.close')" @click="emit('close')"><X :size="14" /></button>
    </header>
    <div v-if="embedded">
      <template v-if="runs.length">
        <div class="muted hidden grid-cols-[minmax(150px,0.8fr)_minmax(190px,1fr)_130px_minmax(180px,1.2fr)_28px] items-center gap-4 border-b border-[var(--border)] bg-[var(--panel-subtle)] px-5 py-2.5 text-[10px] font-semibold lg:grid">
          <span>{{ t('designer.runTrigger') }}</span>
          <span>{{ t('designer.runStartedAt') }}</span>
          <span>{{ t('common.status') }}</span>
          <span>{{ t('designer.runId') }}</span>
          <span></span>
        </div>
        <button
          v-for="item in runs"
          :key="item.id"
          type="button"
          class="grid min-h-[68px] w-full grid-cols-[minmax(0,1fr)_100px_24px] items-center gap-3 border-b border-l-2 border-b-[var(--border)] px-5 text-left transition-colors last:border-b-0 lg:grid-cols-[minmax(150px,0.8fr)_minmax(190px,1fr)_130px_minmax(180px,1.2fr)_28px] lg:gap-4"
          :class="selectedRunId === item.id ? 'border-l-[var(--primary)] bg-[var(--primary-soft)]' : 'border-l-transparent hover:bg-[var(--panel-subtle)]'"
          :aria-current="selectedRunId === item.id ? 'true' : undefined"
          @click="emit('replay', item)"
        >
          <span class="flex min-w-0 items-center gap-3">
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-[var(--panel-subtle)] text-[var(--muted)]"><Activity :size="14" /></span>
            <span class="min-w-0">
              <span class="block truncate text-xs font-semibold">{{ t(`designer.triggerShort.${item.triggered_by || 'studio'}`) }}</span>
              <span class="muted mt-1 block truncate text-[10px] lg:hidden">{{ formatDate(item.created_at) }} {{ formatTime(item.created_at) }}</span>
            </span>
          </span>
          <span class="hidden min-w-0 lg:block"><span class="block text-xs font-medium">{{ formatDate(item.created_at) }}</span><span class="muted mt-1 block text-[10px]">{{ formatTime(item.created_at) }}</span></span>
          <span class="inline-flex h-7 min-w-0 items-center gap-2 justify-self-start rounded-md px-2.5 text-[10px] font-medium" :class="statusTone(item.status)"><span class="h-1.5 w-1.5 shrink-0 rounded-full" :class="statusClass(item.status)"></span><span class="truncate">{{ statusLabel(item.status) }}</span></span>
          <span class="muted hidden min-w-0 truncate font-mono text-[10px] lg:block" :title="item.id">{{ item.id }}</span>
          <ChevronRight :size="15" class="text-[var(--muted)]" />
        </button>
      </template>
      <div v-else class="muted py-14 text-center text-xs">{{ t('designer.noRun') }}</div>
    </div>
    <div v-else class="max-h-80 overflow-y-auto p-2">
      <button v-for="item in runs" :key="item.id" type="button" class="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left hover:bg-[var(--panel-subtle)]" @click="emit('replay', item)">
        <span class="h-2 w-2 shrink-0 rounded-full" :class="statusClass(item.status)"></span>
        <span class="min-w-0 flex-1"><span class="block truncate text-xs font-semibold">{{ t(`designer.triggerShort.${item.triggered_by || 'studio'}`) }} ({{ formatTime(item.created_at) }})</span><span class="muted mt-1 block truncate text-[10px]">{{ new Date(item.created_at).toLocaleString() }} · {{ statusLabel(item.status) }}</span></span>
      </button>
      <div v-if="!runs.length" class="muted py-12 text-center text-xs">{{ t('designer.noRun') }}</div>
    </div>
  </div>
</template>
