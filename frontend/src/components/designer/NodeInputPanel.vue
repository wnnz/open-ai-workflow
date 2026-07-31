<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

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
  <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.inputVariables')" :hint="t('designer.inputVariablesHint')" :count="fields.length" kind="input" collapsible>
    <div class="space-y-3">
      <NodeSettingCard v-for="field in fields" :key="field.key" :title="field.label" :hint="field.hint" :type="field.type" :required="field.required">
        <VariableField :model-value="String(config[field.key] ?? '')" :groups="variableGroups" :placeholder="field.placeholder || ''" @update:model-value="config[field.key] = $event" />
      </NodeSettingCard>
    </div>
  </NodeConfigSection>
</template>
