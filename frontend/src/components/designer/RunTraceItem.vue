<script setup lang="ts">
import { computed, ref } from 'vue'
import { Activity, ChevronDown, LocateFixed } from 'lucide-vue-next'

const props = defineProps<{ item: any; label?: string }>()
const emit = defineEmits<{ focus: [nodeId: string] }>()
const expanded = ref(false)
const duration = computed(() => {
  const milliseconds = Number(props.item?.metadata?.duration_ms)
  if (Number.isFinite(milliseconds)) return milliseconds < 1000 ? `${Math.round(milliseconds)} ms` : `${(milliseconds / 1000).toFixed(2)} s`
  if (!props.item?.started_at || !props.item?.finished_at) return '—'
  return `${Math.max(0, new Date(props.item.finished_at).getTime() - new Date(props.item.started_at).getTime())} ms`
})
const tone = computed(() => props.item?.status === 'succeeded' ? 'text-emerald-600' : props.item?.status === 'waiting' ? 'text-amber-600' : props.item?.status === 'skipped' ? 'text-[var(--muted)]' : 'text-red-600')
</script>

<template>
  <article class="relative flex gap-3">
    <span class="z-10 flex h-8 w-8 shrink-0 items-center justify-center rounded-full border border-[var(--border)] bg-[var(--panel)]" :class="tone"><Activity :size="13" /></span>
    <div class="min-w-0 flex-1 overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]">
      <div class="flex items-center gap-1 px-3 py-2.5">
        <button type="button" class="min-w-0 flex-1 text-left" :aria-expanded="expanded" @click="expanded = !expanded">
          <span class="flex items-center gap-2"><span class="truncate text-xs font-semibold">{{ label || item.node_id }}</span><span class="ml-auto shrink-0 text-[9px]" :class="tone">{{ item.status }}</span></span>
          <span class="muted mt-1 flex gap-2 text-[9px]"><span>{{ item.node_type }}</span><span>·</span><span>{{ duration }}</span><span v-if="item.attempts">· {{ $t('designer.attemptCount', { count: item.attempts }) }}</span></span>
        </button>
        <button type="button" class="icon-button" :title="$t('designer.focusTraceNode')" :aria-label="$t('designer.focusTraceNode')" @click="emit('focus', item.node_id)"><LocateFixed :size="13" /></button>
        <button type="button" class="icon-button" :aria-label="expanded ? $t('designer.collapseSection') : $t('designer.expandSection')" @click="expanded = !expanded"><ChevronDown :size="13" class="transition-transform" :class="expanded && 'rotate-180'" /></button>
      </div>
      <div v-if="expanded" class="space-y-3 border-t border-[var(--border)] bg-[var(--panel)] p-3">
        <section v-if="item.input != null"><h4 class="trace-heading">{{ $t('designer.runInputs') }}</h4><pre class="trace-code">{{ JSON.stringify(item.input, null, 2) }}</pre></section>
        <section v-if="item.output != null"><h4 class="trace-heading">{{ $t('designer.runOutputs') }}</h4><pre class="trace-code">{{ JSON.stringify(item.output, null, 2) }}</pre></section>
        <section v-if="item.error"><h4 class="trace-heading text-red-600">{{ $t('designer.runError') }}</h4><pre class="trace-code text-red-600">{{ item.error }}</pre></section>
        <section v-if="item.metadata"><h4 class="trace-heading">{{ $t('designer.traceMetadata') }}</h4><pre class="trace-code">{{ JSON.stringify(item.metadata, null, 2) }}</pre></section>
      </div>
    </div>
  </article>
</template>

<style scoped>
.trace-heading { color: var(--muted); font-size: 9px; font-weight: 700; letter-spacing: .04em; text-transform: uppercase; }
.trace-code { margin-top: 5px; max-height: 180px; overflow: auto; white-space: pre-wrap; word-break: break-all; border-radius: 6px; background: var(--panel-subtle); padding: 8px; font-size: 9px; line-height: 1.5; }
</style>
