<script setup lang="ts">
import { ShieldCheck, SlidersHorizontal } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import FormField from '@/components/ui/FormField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import Select from '@/volt/Select.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeInputPanel, { type NodeInputField } from './NodeInputPanel.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

props.config.operation ||= 'extract'
props.config.extract_mode ||= 'text'
props.config.page_range ||= ''
props.config.ocr_fallback ??= false

const inputFields: NodeInputField[] = [
  { key: 'source', label: t('designer.sourceFile'), type: 'File', required: true, placeholder: t('designer.variableReferencePlaceholder') },
]
</script>

<template>
  <section class="mt-5" data-testid="document-config-panel">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.nodeParametersHint')" kind="parameters">
      <template #icon><SlidersHorizontal :size="14" /></template>
      <div class="space-y-4">
        <FormField :label="t('designer.extractMode')" :hint="t('designer.documentExtractHint')" hint-after compact>
          <Select v-model="config.extract_mode" class="!h-9 !text-xs"><option value="text">{{ t('designer.extractModes.text') }}</option><option value="text_tables">{{ t('designer.extractModes.textTables') }}</option><option value="text_images">{{ t('designer.extractModes.textImages') }}</option></Select>
        </FormField>
        <div class="flex gap-2 border-t border-[var(--border)] pt-3 text-emerald-700 dark:text-emerald-300"><ShieldCheck :size="14" class="mt-0.5 shrink-0" /><p class="text-[10px] leading-4">{{ t('designer.documentSecurityHint') }}</p></div>
      </div>
    </NodeConfigSection>

    <NodeInputPanel :config="config" :fields="inputFields" :variable-groups="variableGroups" />
  </section>
</template>
