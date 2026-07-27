<script setup lang="ts">
import { FileText, ShieldCheck } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeInputPanel, { type NodeInputField } from './NodeInputPanel.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

props.config.operation ||= 'extract'
props.config.extract_mode ||= 'text'
props.config.page_range ||= ''
props.config.ocr_fallback ??= true
props.config.format ||= 'docx'
props.config.template_file ||= ''
props.config.output_name ||= 'output'
props.config.target_format ||= 'pdf'
props.config.preserve_layout ??= true
props.config.output_format ||= 'pdf'
props.config.split_mode ||= 'pages'
props.config.ranges ||= ''
props.config.languages ||= 'chi_sim+eng'
props.config.ocr_output_format ||= 'text'
props.config.deskew ??= true

const inputFields = computed<NodeInputField[]>(() => {
  switch (props.config.operation) {
    case 'create':
      return [
        { key: 'content', label: t('designer.documentContent'), type: 'String | Object', required: true, placeholder: '{{llm.text}}' },
        { key: 'template_file', label: t('designer.templateFile'), type: 'File', placeholder: '{{inputs.template}}' },
      ]
    case 'merge':
      return [{ key: 'sources', label: t('designer.sourceFiles'), type: 'Array[File]', required: true, placeholder: '{{inputs.files}}' }]
    default:
      return [{ key: 'source', label: t('designer.sourceFile'), type: 'File', required: true, placeholder: '{{inputs.file}}' }]
  }
})
</script>

<template>
  <section class="mt-5 space-y-5" data-testid="document-config-panel">
    <section>
      <div class="mb-2 flex items-center gap-2"><FileText :size="14" class="text-rose-500" /><h3 class="text-xs font-semibold">{{ t('designer.documentOperation') }}</h3></div>
      <Select v-model="config.operation" class="!h-9 !text-xs" :aria-label="t('designer.documentOperation')">
        <option v-for="operation in ['extract','create','convert','merge','split','ocr']" :key="operation" :value="operation">{{ t(`designer.documentOperations.${operation}`) }}</option>
      </Select>
      <p class="muted mt-2 text-[10px]">{{ t(`designer.documentOperationHints.${config.operation}`) }}</p>
    </section>

    <NodeInputPanel :config="config" :fields="inputFields" :variable-groups="variableGroups" />

    <details class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]" open>
      <summary class="cursor-pointer px-3 py-2.5 text-xs font-semibold">{{ t('designer.documentSettings') }}</summary>
      <div class="space-y-4 border-t border-[var(--border)] p-3">
        <template v-if="config.operation === 'extract'">
          <label class="field-label">{{ t('designer.extractMode') }}<Select v-model="config.extract_mode" class="mt-1.5 !h-9 !text-xs"><option value="text">{{ t('designer.extractModes.text') }}</option><option value="text_tables">{{ t('designer.extractModes.textTables') }}</option><option value="text_images">{{ t('designer.extractModes.textImages') }}</option></Select></label>
          <label class="field-label">{{ t('designer.pageRange') }}<InputText v-model="config.page_range" class="mt-1.5" placeholder="1-3,5" /></label>
          <div class="setting-row"><div><h4>{{ t('designer.ocrFallback') }}</h4><p>{{ t('designer.ocrFallbackHint') }}</p></div><ToggleSwitch v-model="config.ocr_fallback" :label="t('designer.ocrFallback')" /></div>
        </template>

        <template v-else-if="config.operation === 'create'">
          <label class="field-label">{{ t('designer.outputFormat') }}<Select v-model="config.format" class="mt-1.5 !h-9 !text-xs"><option value="docx">DOCX</option><option value="xlsx">XLSX</option><option value="pptx">PPTX</option><option value="pdf">PDF</option></Select></label>
          <label class="field-label">{{ t('designer.documentOutputName') }}<InputText v-model="config.output_name" class="mt-1.5" placeholder="output" /></label>
        </template>

        <template v-else-if="config.operation === 'convert'">
          <label class="field-label">{{ t('designer.targetFormat') }}<Select v-model="config.target_format" class="mt-1.5 !h-9 !text-xs"><option v-for="format in ['pdf','docx','xlsx','pptx','txt','html','images']" :key="format" :value="format">{{ format.toUpperCase() }}</option></Select></label>
          <div class="setting-row"><div><h4>{{ t('designer.preserveLayout') }}</h4><p>{{ t('designer.preserveLayoutHint') }}</p></div><ToggleSwitch v-model="config.preserve_layout" :label="t('designer.preserveLayout')" /></div>
        </template>

        <template v-else-if="config.operation === 'merge'">
          <label class="field-label">{{ t('designer.outputFormat') }}<Select v-model="config.output_format" class="mt-1.5 !h-9 !text-xs"><option value="pdf">PDF</option><option value="docx">DOCX</option></Select></label>
          <label class="field-label">{{ t('designer.documentOutputName') }}<InputText v-model="config.output_name" class="mt-1.5" placeholder="merged" /></label>
        </template>

        <template v-else-if="config.operation === 'split'">
          <label class="field-label">{{ t('designer.splitMode') }}<Select v-model="config.split_mode" class="mt-1.5 !h-9 !text-xs"><option value="pages">{{ t('designer.splitModes.pages') }}</option><option value="ranges">{{ t('designer.splitModes.ranges') }}</option><option value="sheets">{{ t('designer.splitModes.sheets') }}</option><option value="slides">{{ t('designer.splitModes.slides') }}</option></Select></label>
          <label v-if="config.split_mode === 'ranges'" class="field-label">{{ t('designer.pageRange') }}<InputText v-model="config.ranges" class="mt-1.5" placeholder="1-3,4-6" /></label>
        </template>

        <template v-else>
          <label class="field-label">{{ t('designer.ocrLanguages') }}<InputText v-model="config.languages" class="mt-1.5" placeholder="chi_sim+eng" /></label>
          <label class="field-label">{{ t('designer.outputFormat') }}<Select v-model="config.ocr_output_format" class="mt-1.5 !h-9 !text-xs"><option value="text">TEXT</option><option value="searchable_pdf">{{ t('designer.searchablePdf') }}</option><option value="json">JSON</option></Select></label>
          <div class="setting-row"><div><h4>{{ t('designer.deskew') }}</h4><p>{{ t('designer.deskewHint') }}</p></div><ToggleSwitch v-model="config.deskew" :label="t('designer.deskew')" /></div>
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
