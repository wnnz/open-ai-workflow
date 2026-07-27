<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import NodeConfigSection from './NodeConfigSection.vue'

export type NodeInputField = {
  key: string
  label: string
  type?: string
  required?: boolean
  placeholder?: string
  hint?: string
}

defineProps<{ config: Record<string, any>; fields: NodeInputField[]; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()
</script>

<template>
  <NodeConfigSection class="mt-5" :title="t('designer.inputVariables')" :hint="t('designer.inputVariablesHint')" :count="fields.length" collapsible>
    <div class="space-y-3">
      <div v-for="field in fields" :key="field.key">
        <div class="mb-1.5 flex items-center gap-1.5 text-[11px] font-semibold">
          <span>{{ field.label }}</span><span v-if="field.required" class="text-red-500">*</span>
          <span v-if="field.type" class="muted ml-auto rounded bg-[var(--panel-subtle)] px-1.5 py-0.5 font-mono text-[9px] font-normal">{{ field.type }}</span>
        </div>
        <VariableField :model-value="String(config[field.key] ?? '')" :groups="variableGroups" :placeholder="field.placeholder || ''" @update:model-value="config[field.key] = $event" />
        <p v-if="field.hint" class="muted mt-1 text-[10px]">{{ field.hint }}</p>
      </div>
    </div>
  </NodeConfigSection>
</template>
