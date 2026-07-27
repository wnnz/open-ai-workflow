<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { AlertCircle, CheckCircle2, Clock3, Play, X } from 'lucide-vue-next'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import WorkflowInputField from '@/components/WorkflowInputField.vue'
import Button from '@/volt/Button.vue'
import RunTraceItem from './RunTraceItem.vue'

const props = defineProps<{
  open: boolean
  title: string
  fields: any[]
  inputs: Record<string, any>
  uploadingField: string
  result: any
  error: string
  running: boolean
  nodeRun?: boolean
  readonly?: boolean
  nodeLabels?: Record<string, string>
}>()
const emit = defineEmits<{
  close: []
  run: []
  fileChange: [field: any, event: Event]
  focusNode: [nodeId: string]
}>()

const activeTab = ref<'input' | 'result' | 'detail' | 'trace'>('input')
const tabs = computed(() => props.readonly ? ['result', 'detail', 'trace'] as const : ['input', 'result', 'detail', 'trace'] as const)
const statusTone = computed(() => props.result?.status === 'succeeded' ? 'text-emerald-600' : props.result?.status === 'waiting' ? 'text-amber-600' : props.result?.status === 'failed' ? 'text-red-600' : 'text-[var(--muted)]')

watch(() => props.open, value => { if (value) activeTab.value = props.readonly ? 'result' : 'input' }, { immediate: true })
watch(() => props.result?.id, value => { if (value) activeTab.value = props.result?.status === 'waiting' ? 'trace' : 'result' })

</script>

<template>
  <Transition name="debug-panel">
    <aside v-if="open" class="fixed inset-y-0 right-0 z-[70] flex w-[430px] max-w-[94vw] flex-col border-l border-[var(--border)] bg-[var(--panel)] shadow-[-18px_0_45px_rgba(15,23,42,0.12)]">
      <header class="flex h-16 shrink-0 items-center gap-3 border-b border-[var(--border)] px-5">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><Play :size="15" /></span>
        <div class="min-w-0 flex-1"><h2 class="truncate text-sm font-semibold">{{ title }}</h2><p class="muted mt-0.5 text-[10px]">{{ readonly ? $t('designer.readOnlyReplayHint') : nodeRun ? $t('designer.runNodeHint') : $t('designer.testInputs') }}</p></div>
        <span v-if="result" class="text-[10px] font-medium" :class="statusTone">{{ result.status }}</span>
        <button type="button" class="icon-button" :aria-label="$t('common.close')" @click="emit('close')"><X :size="15" /></button>
      </header>

      <nav class="flex shrink-0 border-b border-[var(--border)] px-4">
        <button v-for="tab in tabs" :key="tab" type="button" class="inspector-tab" :class="{ active: activeTab === tab }" @click="activeTab = tab">
          {{ tab === 'input' ? $t('designer.runInputs') : tab === 'result' ? $t('designer.runOutputs') : tab === 'detail' ? $t('designer.runDetail') : $t('designer.nodeTrace') }}
        </button>
      </nav>

      <div class="min-h-0 flex-1 overflow-y-auto p-5">
        <form v-if="activeTab === 'input'" class="space-y-4" @submit.prevent="emit('run')">
          <WorkflowInputField v-for="field in fields" :key="field.name" v-model="inputs[field.name]" :field="field" :uploading="uploadingField === field.name" @file-change="emit('fileChange', field, $event)" />
          <div v-if="!fields.length" class="rounded-lg border border-dashed border-[var(--border)] py-10 text-center text-xs text-[var(--muted)]">{{ $t('designer.noWorkflowInputs') }}</div>
          <AlertBanner :message="error" tone="error" />
          <Button type="submit" class="!mt-6 w-full justify-center" :loading="running"><Play :size="14" />{{ nodeRun ? $t('designer.runStep') : $t('workflow.run') }}</Button>
        </form>

        <div v-else-if="activeTab === 'result'">
          <div v-if="result" class="space-y-4">
            <div class="flex items-center gap-2 text-xs font-semibold" :class="statusTone"><CheckCircle2 v-if="result.status === 'succeeded'" :size="15" /><Clock3 v-else-if="result.status === 'waiting'" :size="15" /><AlertCircle v-else :size="15" />{{ result.status }}</div>
            <pre class="overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-[11px] leading-5 text-slate-100">{{ JSON.stringify(result.outputs || {}, null, 2) }}</pre>
            <AlertBanner :message="result.error || error" tone="error" />
          </div>
          <div v-else class="muted py-16 text-center text-xs">{{ $t('designer.noRun') }}</div>
        </div>

        <div v-else-if="activeTab === 'detail'">
          <dl v-if="result" class="overflow-hidden rounded-lg border border-[var(--border)] text-xs">
            <div v-for="item in [[$t('common.status'), result.status], ['Run ID', result.id], [$t('designer.runInputs'), JSON.stringify(result.inputs || {})], [$t('designer.runOutputs'), JSON.stringify(result.outputs || {})], [$t('designer.runError'), result.error || '—']]" :key="String(item[0])" class="grid grid-cols-[110px_minmax(0,1fr)] border-b border-[var(--border)] last:border-0"><dt class="bg-[var(--panel-subtle)] px-3 py-3 font-medium">{{ item[0] }}</dt><dd class="break-all px-3 py-3 font-mono text-[11px]">{{ item[1] }}</dd></div>
          </dl>
          <div v-else class="muted py-16 text-center text-xs">{{ $t('designer.noRun') }}</div>
        </div>

        <div v-else>
          <div v-if="result?.trace?.length" class="relative space-y-3 before:absolute before:bottom-5 before:left-[15px] before:top-5 before:w-px before:bg-[var(--border)]">
            <RunTraceItem v-for="(item, index) in result.trace" :key="`${item.node_id}-${index}`" :item="item" :label="nodeLabels?.[item.node_id]" @focus="emit('focusNode', $event)" />
          </div>
          <div v-else class="muted py-16 text-center text-xs">{{ $t('designer.noRun') }}</div>
        </div>
      </div>
    </aside>
  </Transition>
</template>

<style scoped>
.debug-panel-enter-active,.debug-panel-leave-active{transition:transform .2s ease,opacity .2s ease}.debug-panel-enter-from,.debug-panel-leave-to{transform:translateX(100%);opacity:.6}
</style>
