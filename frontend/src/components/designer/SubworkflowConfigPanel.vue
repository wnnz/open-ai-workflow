<script setup lang="ts">
import { computed } from 'vue'
import { GitBranch, LockKeyhole } from 'lucide-vue-next'
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import Select from '@/volt/Select.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

const props = defineProps<{
  config: Record<string, any>
  workflows: any[]
  variableGroups: any[]
}>()
const emit = defineEmits<{ select: [] }>()

const target = computed(() => props.workflows.find(item => item.id === props.config.workflow_id))
const inputFields = computed(() => {
  const start = target.value?.draft_graph?.nodes?.find((node: any) => node.type === 'start' && !node.parentNode)
  return Array.isArray(start?.data?.config?.input_fields) ? start.data.config.input_fields : []
})

function selectTarget() {
  emit('select')
  const nextInputs: Record<string, any> = {}
  for (const field of inputFields.value) {
    const name = String(field.name || '')
    if (name) nextInputs[name] = props.config.inputs?.[name] ?? ''
  }
  props.config.inputs = nextInputs
}
</script>

<template>
  <section class="mt-5">
    <NodeConfigSection :title="$t('designer.nodeParameters')" :hint="$t('designer.nodeParametersHint')" kind="parameters">
      <div class="space-y-4">
        <FormField :label="$t('designer.targetWorkflow')" required compact><Select v-model="config.workflow_id" @change="selectTarget"><option value="">{{ $t('designer.selectWorkflow') }}</option><option v-for="item in workflows" :key="item.id" :value="item.id">{{ item.name }}</option></Select></FormField>
        <p v-if="!workflows.length" class="resource-empty">{{ $t('designer.noSubworkflows') }}</p>
        <NodeSettingCard v-if="target"><div class="flex items-center gap-2 text-xs font-semibold"><GitBranch :size="14" class="text-emerald-600" />{{ target.name }}</div><div class="muted mt-2 flex items-center gap-1.5 text-[10px]"><LockKeyhole :size="11" />{{ target.published_version_id ? $t('designer.subworkflowPublishedPin') : $t('designer.subworkflowDraftOnly') }}</div></NodeSettingCard>
      </div>
    </NodeConfigSection>

    <NodeConfigSection v-if="target" class="mt-5 border-t border-[var(--border)] pt-5" :title="$t('designer.inputVariables')" :hint="$t('designer.inputMappingHint')" :count="inputFields.length" kind="input" collapsible>
      <div v-if="inputFields.length" class="space-y-3"><NodeSettingCard v-for="field in inputFields" :key="field.name" :title="field.label || field.name" :type="field.type || 'Any'" :required="field.required"><VariableField v-model="config.inputs[field.name]" :groups="variableGroups" :placeholder="$t('designer.variableReferencePlaceholder')" /></NodeSettingCard></div>
      <p v-else class="resource-empty">{{ $t('designer.noWorkflowInputs') }}</p>
    </NodeConfigSection>
  </section>
</template>
