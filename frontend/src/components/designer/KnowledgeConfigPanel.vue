<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeInputPanel from './NodeInputPanel.vue'

const props = defineProps<{ config: any; datasets: any[]; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

props.config.dataset_ids = Array.isArray(props.config.dataset_ids)
  ? [...new Set(props.config.dataset_ids.filter(Boolean))]
  : props.config.dataset_id ? [props.config.dataset_id] : []
props.config.retrieval_mode ||= 'hybrid'
props.config.rerank = { mode: 'weighted', semantic_weight: 0.7, model_name: '', ...(props.config.rerank || {}) }
props.config.score_threshold = { enabled: Number(props.config.threshold) > 0, value: Number(props.config.threshold ?? 0.2), ...(props.config.score_threshold || {}) }
props.config.metadata_filter = { enabled: false, logical_operator: 'and', conditions: [], ...(props.config.metadata_filter || {}) }

const keywordWeight = computed(() => Math.max(0, 1 - Number(props.config.rerank.semantic_weight || 0)))
function selected(id: string) { return props.config.dataset_ids.includes(id) }
function toggleDataset(dataset: any) {
  props.config.dataset_ids = selected(dataset.id) ? props.config.dataset_ids.filter((id: string) => id !== dataset.id) : [...props.config.dataset_ids, dataset.id]
  props.config.dataset_id = props.config.dataset_ids[0] || ''
  props.config.dataset_names = props.datasets.filter(item => props.config.dataset_ids.includes(item.id)).map(item => item.name)
  props.config.dataset_name = props.config.dataset_names[0] || ''
}
function addFilter() { props.config.metadata_filter.conditions.push({ key: '', operator: 'equals', value: '' }) }
function removeFilter(index: number) { props.config.metadata_filter.conditions.splice(index, 1) }
</script>

<template>
  <section class="mt-5 space-y-5">
    <NodeInputPanel :config="config" :fields="[{ key: 'query', label: t('designer.queryText'), type: 'String', required: true, placeholder: t('designer.variableReferencePlaceholder') }]" :variable-groups="variableGroups" />

    <section>
      <div class="flex items-center"><div><h3 class="text-xs font-semibold">{{ t('designer.knowledgeBases') }} <span class="text-red-500">*</span></h3><p class="muted mt-1 text-[11px]">{{ t('designer.knowledgeBasesHint') }}</p></div><span class="muted ml-auto text-[10px]">{{ config.dataset_ids.length }}</span></div>
      <div class="mt-3 space-y-2">
        <button v-for="dataset in datasets" :key="dataset.id" type="button" class="flex w-full items-center gap-3 rounded-lg border p-3 text-left" :class="selected(dataset.id) ? 'border-[var(--primary)] bg-[var(--primary-soft)]' : 'border-[var(--border)] bg-[var(--panel-subtle)]'" @click="toggleDataset(dataset)">
          <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-amber-50 text-sm dark:bg-amber-950/40">📚</span><span class="min-w-0 flex-1"><span class="block truncate text-xs font-semibold">{{ dataset.name }}</span><span class="muted mt-1 block truncate text-[10px]">{{ dataset.description || t('designer.noDatasetDescription') }}</span></span><span class="flex h-4 w-4 items-center justify-center rounded border text-[10px]" :class="selected(dataset.id) ? 'border-[var(--primary)] bg-[var(--primary)] text-white' : 'border-[var(--border)]'">{{ selected(dataset.id) ? '✓' : '' }}</span>
        </button>
        <div v-if="!datasets.length" class="resource-empty">{{ t('designer.noKnowledge') }}</div>
      </div>
    </section>

    <details class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]" open>
      <summary class="cursor-pointer px-3 py-2.5 text-xs font-semibold">{{ t('designer.retrievalSettings') }}</summary>
      <div class="space-y-4 border-t border-[var(--border)] p-3">
        <label class="field-label">{{ t('designer.retrievalMode') }}<Select v-model="config.retrieval_mode" class="mt-1.5 !h-9 !text-xs"><option value="hybrid">{{ t('designer.retrievalModes.hybrid') }}</option><option value="vector">{{ t('designer.retrievalModes.vector') }}</option><option value="fulltext">{{ t('designer.retrievalModes.fulltext') }}</option></Select></label>
        <div v-if="config.retrieval_mode === 'hybrid'">
          <div class="mb-2 text-[11px] font-semibold">{{ t('designer.rerankStrategy') }}</div>
          <div class="grid grid-cols-2 gap-2" role="radiogroup"><button v-for="mode in ['weighted','model']" :key="mode" type="button" role="radio" :aria-checked="config.rerank.mode === mode" class="rounded-lg border px-3 py-2 text-xs" :class="config.rerank.mode === mode ? 'border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--primary)]' : 'border-[var(--border)]'" @click="config.rerank.mode = mode">{{ t(`designer.rerankModes.${mode}`) }}</button></div>
          <label v-if="config.rerank.mode === 'weighted'" class="field-label mt-3">{{ t('designer.semanticWeight') }}<div class="mt-2 flex items-center gap-3"><input v-model.number="config.rerank.semantic_weight" type="range" min="0" max="1" step="0.1" class="min-w-0 flex-1 accent-[var(--primary)]"><span class="w-8 text-right text-xs">{{ Number(config.rerank.semantic_weight).toFixed(1) }}</span></div><div class="muted mt-1 text-[10px]">{{ t('designer.keywordWeight') }} {{ keywordWeight.toFixed(1) }}</div></label>
          <label v-else class="field-label mt-3">{{ t('designer.rerankModel') }}<InputText v-model="config.rerank.model_name" class="mt-1.5" placeholder="bge-reranker-v2-m3" /></label>
        </div>
        <label class="field-label">Top K<InputText v-model.number="config.top_k" class="mt-1.5" type="number" min="1" max="100" /></label>
        <div class="rounded-lg border border-[var(--border)] bg-[var(--panel)] p-3"><div class="flex items-center gap-3"><div class="min-w-0 flex-1"><h4 class="text-[11px] font-semibold">{{ t('designer.scoreThreshold') }}</h4><p class="muted mt-1 text-[10px]">{{ t('designer.scoreThresholdHint') }}</p></div><ToggleSwitch v-model="config.score_threshold.enabled" :label="t('designer.scoreThreshold')" /></div><InputText v-if="config.score_threshold.enabled" v-model.number="config.score_threshold.value" class="mt-3" type="number" min="0" max="1" step="0.05" /></div>
      </div>
    </details>

    <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
      <div class="flex items-center gap-3"><div class="min-w-0 flex-1"><h3 class="text-xs font-semibold">{{ t('designer.metadataFilter') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.metadataFilterHint') }}</p></div><ToggleSwitch v-model="config.metadata_filter.enabled" :label="t('designer.metadataFilter')" /></div>
      <div v-if="config.metadata_filter.enabled" class="mt-3 border-t border-[var(--border)] pt-3">
        <div class="flex items-center"><Select v-model="config.metadata_filter.logical_operator" class="!h-8 !w-24 !text-xs"><option value="and">AND</option><option value="or">OR</option></Select><button type="button" class="icon-button ml-auto" :aria-label="t('designer.addMetadataCondition')" @click="addFilter"><Plus :size="13" /></button></div>
        <div class="mt-2 space-y-2"><div v-for="(condition, index) in config.metadata_filter.conditions" :key="index" class="grid grid-cols-[1fr_100px_1fr_30px] items-center gap-2"><InputText v-model="condition.key" class="!h-8" :placeholder="t('designer.metadataKey')" /><Select v-model="condition.operator" class="!h-8 !text-xs"><option value="equals">=</option><option value="not_equals">≠</option><option value="contains">{{ t('designer.contains') }}</option><option value="in">IN</option></Select><VariableField v-model="condition.value" :groups="variableGroups" control-class="!h-8" :placeholder="t('designer.metadataValue')" /><button type="button" class="icon-button !h-8 !w-8 text-red-600" :aria-label="t('designer.removeMetadataCondition')" @click="removeFilter(Number(index))"><Trash2 :size="13" /></button></div></div>
        <button v-if="!config.metadata_filter.conditions.length" type="button" class="mt-2 w-full rounded-md border border-dashed border-[var(--border)] py-3 text-[11px] text-[var(--muted)]" @click="addFilter"><Plus class="mr-1 inline" :size="12" />{{ t('designer.addMetadataCondition') }}</button>
      </div>
    </section>
  </section>
</template>
