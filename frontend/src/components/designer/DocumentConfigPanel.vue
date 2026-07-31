<script setup lang="ts">
import { FileText, ShieldCheck } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import NodeInputPanel, { type NodeInputField } from './NodeInputPanel.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

props.config.operation ||= 'extract'
props.config.extract_mode ||= 'text'
props.config.page_range ||= ''
props.config.ocr_fallback ??= false
props.config.answers ||= ''
props.config.output_name ||= '英语试卷_已作答.docx'

const inputFields = computed<NodeInputField[]>(() => {
  const fields: NodeInputField[] = [
    { key: 'source', label: t('designer.sourceFile'), type: 'File', required: true, placeholder: t('designer.variableReferencePlaceholder') },
  ]
  if (props.config.operation === 'fill_answers') fields.push(
    { key: 'answers', label: t('designer.answerPlan'), type: 'Object', required: true, placeholder: t('designer.variableReferencePlaceholder') },
  )
  return fields
})
</script>

<template>
  <section class="mt-5 space-y-5" data-testid="document-config-panel">
    <section>
      <div class="mb-2 flex items-center gap-2"><FileText :size="14" class="text-rose-500" /><h3 class="text-xs font-semibold">{{ t('designer.documentOperation') }}</h3></div>
      <Select v-model="config.operation" class="!h-9 !text-xs" :aria-label="t('designer.documentOperation')">
        <option v-for="operation in ['extract','fill_answers']" :key="operation" :value="operation">{{ t(`designer.documentOperations.${operation}`) }}</option>
      </Select>
      <p class="muted mt-2 text-[10px]">{{ t(`designer.documentOperationHints.${config.operation}`) }}</p>
    </section>

    <NodeInputPanel :config="config" :fields="inputFields" :variable-groups="variableGroups" />

    <details class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]" open>
      <summary class="cursor-pointer px-3 py-2.5 text-xs font-semibold">{{ t('designer.documentSettings') }}</summary>
      <div class="space-y-4 border-t border-[var(--border)] p-3">
        <template v-if="config.operation === 'extract'">
          <label class="field-label">{{ t('designer.extractMode') }}<Select v-model="config.extract_mode" class="mt-1.5 !h-9 !text-xs"><option value="text">{{ t('designer.extractModes.text') }}</option><option value="text_tables">{{ t('designer.extractModes.textTables') }}</option><option value="text_images">{{ t('designer.extractModes.textImages') }}</option></Select></label>
          <p class="muted text-[10px] leading-4">DOCX</p>
        </template>
        <template v-else>
          <label class="field-label">{{ t('designer.documentOutputName') }}<InputText v-model="config.output_name" class="mt-1.5" placeholder="英语试卷_已作答.docx" /></label>
        </template>
      </div>
    </details>

    <div class="flex gap-2 rounded-lg border border-emerald-200 bg-emerald-50 p-3 text-emerald-800 dark:border-emerald-900 dark:bg-emerald-950/30 dark:text-emerald-300"><ShieldCheck :size="15" class="mt-0.5 shrink-0" /><p class="text-[10px] leading-4">{{ t('designer.documentSecurityHint') }}</p></div>
  </section>
</template>

<style scoped>
.setting-row { display:flex; align-items:center; gap:.75rem; border:1px solid var(--border); border-radius:.5rem; background:var(--panel); padding:.75rem; }
.setting-row > div { min-width:0; flex:1; }
.setting-row h4 { font-size:.6875rem; font-weight:600; }
.setting-row p { margin-top:.25rem; color:var(--muted); font-size:.625rem; line-height:1rem; }
</style>
