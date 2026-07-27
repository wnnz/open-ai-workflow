<script setup lang="ts">
import { Activity, RefreshCw, X } from 'lucide-vue-next'

defineProps<{ open: boolean; runs: any[] }>()
const emit = defineEmits<{ close: []; refresh: []; replay: [run: any] }>()

function statusClass(status: string) {
  return status === 'succeeded' ? 'bg-emerald-500' : status === 'failed' ? 'bg-red-500' : 'bg-amber-500'
}
</script>

<template>
  <div v-if="open" class="surface absolute right-0 top-10 z-[60] w-80 overflow-hidden rounded-xl shadow-2xl">
    <header class="flex h-12 items-center gap-2 border-b border-[var(--border)] px-4">
      <Activity :size="15" class="text-[var(--primary)]" />
      <h2 class="text-sm font-semibold">{{ $t('designer.runHistory') }}</h2>
      <button type="button" class="icon-button ml-auto" :title="$t('common.refresh')" @click="emit('refresh')"><RefreshCw :size="14" /></button>
      <button type="button" class="icon-button" :aria-label="$t('common.close')" @click="emit('close')"><X :size="14" /></button>
    </header>
    <div class="max-h-80 overflow-y-auto p-2">
      <button v-for="item in runs" :key="item.id" type="button" class="flex w-full items-center gap-3 rounded-lg px-3 py-3 text-left hover:bg-[var(--panel-subtle)]" @click="emit('replay', item)">
        <span class="h-2 w-2 shrink-0 rounded-full" :class="statusClass(item.status)"></span>
        <span class="min-w-0 flex-1"><span class="block truncate text-xs font-semibold">{{ $t(`designer.triggerShort.${item.triggered_by || 'studio'}`) }} ({{ new Date(item.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' }) }})</span><span class="muted mt-1 block truncate text-[10px]">{{ new Date(item.created_at).toLocaleString() }} · {{ item.status }}</span></span>
      </button>
      <div v-if="!runs.length" class="muted py-12 text-center text-xs">{{ $t('designer.noRun') }}</div>
    </div>
  </div>
</template>
