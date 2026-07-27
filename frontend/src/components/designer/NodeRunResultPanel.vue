<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertCircle, CheckCircle2, Clock3, RotateCcw } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import AlertBanner from '@/components/ui/AlertBanner.vue'

const props = defineProps<{ result: any | null }>()
const { t } = useI18n()
const activeTab = ref<'input' | 'process' | 'output' | 'detail'>('output')
watch(() => props.result?.node_id, () => { activeTab.value = 'output' })
const duration = computed(() => {
  if (!props.result?.started_at || !props.result?.finished_at) return null
  const value = new Date(props.result.finished_at).getTime() - new Date(props.result.started_at).getTime()
  return Number.isFinite(value) && value >= 0 ? value : null
})
const statusTone = computed(() => props.result?.status === 'succeeded' ? 'success' : props.result?.status === 'recovered' || props.result?.status === 'waiting' ? 'warning' : 'danger')
const statusLabel = computed(() => props.result?.status ? t(`designer.runStatus.${props.result.status}`) : '')
const usage = computed(() => ({ input_tokens: 0, output_tokens: 0, total_tokens: 0, ...(props.result?.metadata?.usage || {}) }))
function json(value: any) {
  if (value === undefined) return '{}'
  try { return JSON.stringify(value, null, 2) } catch { return String(value) }
}
function formatTime(value: string | null | undefined) { return value ? new Date(value).toLocaleString() : '—' }
</script>

<template>
  <div v-if="result" class="space-y-4">
    <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
      <div class="flex items-center gap-2">
        <span class="run-status-icon" :class="`status-${statusTone}`"><CheckCircle2 v-if="result.status === 'succeeded'" :size="15" /><Clock3 v-else-if="result.status === 'waiting'" :size="15" /><RotateCcw v-else-if="result.status === 'recovered'" :size="15" /><AlertCircle v-else :size="15" /></span>
        <div><div class="text-xs font-semibold">{{ statusLabel }}</div><div class="muted mt-0.5 text-[9px]">{{ result.node_type }} · {{ result.node_id }}</div></div>
        <div class="ml-auto text-right"><div class="text-xs font-semibold">{{ duration == null ? '—' : `${duration} ms` }}</div><div class="muted mt-0.5 text-[9px]">{{ $t('designer.runDuration') }}</div></div>
      </div>
      <div class="mt-3 grid grid-cols-3 gap-2 text-[10px]"><div class="rounded-md bg-[var(--panel)] px-2.5 py-2"><span class="muted block">{{ $t('designer.runStartedAt') }}</span><span class="mt-1 block truncate">{{ formatTime(result.started_at) }}</span></div><div class="rounded-md bg-[var(--panel)] px-2.5 py-2"><span class="muted block">{{ $t('designer.runAttempts') }}</span><span class="mt-1 block">{{ result.attempts || 1 }}</span></div><div class="rounded-md bg-[var(--panel)] px-2.5 py-2"><span class="muted block">{{ $t('designer.totalTokens') }}</span><span class="mt-1 block">{{ usage.total_tokens }} Tokens</span></div></div>
    </section>

    <nav class="flex border-b border-[var(--border)]">
      <button v-for="tab in ['input','process','output','detail'] as const" :key="tab" type="button" class="inspector-tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">{{ tab === 'input' ? $t('designer.runInputs') : tab === 'process' ? $t('designer.dataProcessing') : tab === 'output' ? $t('designer.runOutputs') : $t('designer.runDetail') }}</button>
    </nav>

    <div v-if="activeTab === 'input'">
      <pre class="run-json">{{ json(result.input) }}</pre>
      <p v-if="result.input == null" class="muted mt-2 text-center text-[10px]">{{ $t('designer.noNodeInput') }}</p>
    </div>
    <div v-else-if="activeTab === 'process'" class="space-y-3">
      <dl class="overflow-hidden rounded-lg border border-[var(--border)] text-[10px]">
        <div v-for="item in [[$t('designer.executor'), result.metadata?.executor || '—'], [$t('designer.inputSize'), `${result.metadata?.input_bytes || 0} B`], [$t('designer.outputSize'), `${result.metadata?.output_bytes || 0} B`], [$t('designer.retryCount'), result.metadata?.retry_count || 0], [$t('designer.inputTokens'), usage.input_tokens], [$t('designer.outputTokens'), usage.output_tokens]]" :key="String(item[0])" class="grid grid-cols-[115px_minmax(0,1fr)] border-b border-[var(--border)] last:border-0"><dt class="bg-[var(--panel-subtle)] px-3 py-2.5 font-medium">{{ item[0] }}</dt><dd class="break-all px-3 py-2.5 font-mono">{{ item[1] }}</dd></div>
      </dl>
      <div><h4 class="mb-2 text-[10px] font-semibold">{{ $t('designer.runLogs') }}</h4><pre v-if="result.metadata?.logs?.length" class="run-json">{{ result.metadata.logs.join('\n') }}</pre><p v-else class="muted rounded-lg border border-dashed border-[var(--border)] py-8 text-center text-[10px]">{{ $t('designer.noProcessLogs') }}</p></div>
    </div>
    <div v-else-if="activeTab === 'output'">
      <pre class="run-json">{{ json(result.output) }}</pre>
      <p v-if="result.output == null" class="muted mt-2 text-center text-[10px]">{{ $t('designer.noNodeOutput') }}</p>
    </div>
    <dl v-else class="overflow-hidden rounded-lg border border-[var(--border)] text-[10px]">
      <div v-for="item in [[$t('common.status'), statusLabel], [$t('designer.runStartedAt'), formatTime(result.started_at)], [$t('designer.runFinishedAt'), formatTime(result.finished_at)], [$t('designer.runDuration'), duration == null ? '—' : `${duration} ms`], [$t('designer.runAttempts'), result.attempts || 1], [$t('designer.totalTokens'), usage.total_tokens]]" :key="String(item[0])" class="grid grid-cols-[115px_minmax(0,1fr)] border-b border-[var(--border)] last:border-0"><dt class="bg-[var(--panel-subtle)] px-3 py-2.5 font-medium">{{ item[0] }}</dt><dd class="break-all px-3 py-2.5">{{ item[1] }}</dd></div>
    </dl>
    <AlertBanner :message="result.error" tone="error" />
  </div>
  <div v-else class="muted py-16 text-center text-xs">{{ $t('designer.noRun') }}</div>
</template>

<style scoped>
.run-status-icon { display: flex; width: 30px; height: 30px; align-items: center; justify-content: center; border-radius: 8px; }.status-success { background: #ecfdf3; color: #079455; }.status-warning { background: #fffaeb; color: #dc6803; }.status-danger { background: #fef3f2; color: #d92d20; }
.run-json { max-height: 340px; overflow: auto; white-space: pre-wrap; overflow-wrap: anywhere; border-radius: 8px; background: #0f172a; padding: 14px; color: #e2e8f0; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: 10px; line-height: 18px; }
:global(.dark) .status-success { background: rgb(6 78 59 / 35%); color: #6ee7b7; }:global(.dark) .status-warning { background: rgb(120 53 15 / 35%); color: #fcd34d; }:global(.dark) .status-danger { background: rgb(127 29 29 / 35%); color: #fca5a5; }
</style>
