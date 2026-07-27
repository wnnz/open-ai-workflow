<script setup lang="ts">
import { computed } from 'vue'
import { GitBranch, LockKeyhole } from 'lucide-vue-next'
import VariableField from '@/components/VariableField.vue'
import Select from '@/volt/Select.vue'

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
    if (name) nextInputs[name] = props.config.inputs?.[name] ?? `{{inputs.${name}}}`
  }
  props.config.inputs = nextInputs
}
</script>

<template>
  <section class="mt-5 space-y-5">
    <label class="field-label">
      {{ $t('designer.targetWorkflow') }}
      <Select v-model="config.workflow_id" class="mt-1.5 !h-9 !text-xs" @change="selectTarget">
        <option value="">{{ $t('designer.selectWorkflow') }}</option>
        <option v-for="item in workflows" :key="item.id" :value="item.id">{{ item.name }}</option>
      </Select>
    </label>
    <p v-if="!workflows.length" class="resource-empty">{{ $t('designer.noSubworkflows') }}</p>

    <div v-if="target" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
      <div class="flex items-center gap-2 text-xs font-semibold"><GitBranch :size="14" class="text-emerald-600" />{{ target.name }}</div>
      <div class="muted mt-2 flex items-center gap-1.5 text-[10px]"><LockKeyhole :size="11" />{{ target.published_version_id ? $t('designer.subworkflowPublishedPin') : $t('designer.subworkflowDraftOnly') }}</div>
    </div>

    <div v-if="target">
      <h3 class="text-xs font-semibold">{{ $t('designer.inputMapping') }}</h3>
      <p class="muted mt-1 text-[11px]">{{ $t('designer.inputMappingHint') }}</p>
      <div v-if="inputFields.length" class="mt-3 space-y-3">
        <label v-for="field in inputFields" :key="field.name" class="field-label">
          <span class="flex items-center gap-1">{{ field.label || field.name }}<code class="muted text-[9px]">{{ field.name }}</code><span v-if="field.required" class="text-red-500">*</span></span>
          <VariableField v-model="config.inputs[field.name]" class="mt-1.5" :groups="variableGroups" :placeholder="`{{inputs.${field.name}}}`" />
        </label>
      </div>
      <p v-else class="resource-empty mt-3">{{ $t('designer.noWorkflowInputs') }}</p>
    </div>
  </section>
</template>
