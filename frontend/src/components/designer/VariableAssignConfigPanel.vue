<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

if (!Array.isArray(props.config.assignments)) {
  props.config.assignments = Object.entries(props.config.values || {}).map(([name, value]) => ({
    name,
    type: 'Any',
    operation: 'overwrite',
    value,
  }))
}

function addAssignment() {
  let index = props.config.assignments.length + 1
  const names = new Set(props.config.assignments.map((item: any) => item?.name))
  while (names.has(`variable${index}`)) index += 1
  props.config.assignments.push({ name: `variable${index}`, type: 'String', operation: 'overwrite', value: '' })
}
</script>

<template>
  <div data-testid="variable-assign-config-panel" class="mt-5">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.variableAssignmentsHint')" kind="parameters">
      <template #actions><IconButton :label="t('designer.addVariableAssignment')" size="sm" @click="addAssignment"><Plus :size="14" /></IconButton></template>
      <div class="space-y-3">
        <NodeSettingCard v-for="(assignment, index) in config.assignments" :key="index">
          <div class="grid grid-cols-[minmax(0,1fr)_92px_28px] gap-2">
            <InputText v-model="assignment.name" class="font-mono" placeholder="variable1" />
            <Select v-model="assignment.type"><option v-for="type in ['String','Number','Boolean','Object','Array','Any']" :key="type" :value="type">{{ type }}</option></Select>
            <IconButton :label="t('designer.removeVariableAssignment')" tone="danger" size="sm" @click="config.assignments.splice(Number(index), 1)"><Trash2 :size="13" /></IconButton>
          </div>
          <div class="mt-2 grid grid-cols-[104px_minmax(0,1fr)] gap-2">
            <Select v-model="assignment.operation"><option value="overwrite">{{ t('designer.assignmentOperations.overwrite') }}</option><option value="append">{{ t('designer.assignmentOperations.append') }}</option><option value="extend">{{ t('designer.assignmentOperations.extend') }}</option><option value="clear">{{ t('designer.assignmentOperations.clear') }}</option></Select>
            <VariableField v-if="assignment.operation !== 'clear'" v-model="assignment.value" class="min-w-0 font-mono" :groups="variableGroups" :placeholder="t('designer.assignmentValuePlaceholder')" />
            <div v-else class="flex h-9 items-center rounded-lg border border-[var(--border)] bg-[var(--panel)] px-3 text-[11px] text-[var(--muted)]">{{ t('designer.assignmentClearHint') }}</div>
          </div>
        </NodeSettingCard>
        <button v-if="!config.assignments.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addAssignment"><Plus :size="14" />{{ t('designer.addVariableAssignment') }}</button>
      </div>
    </NodeConfigSection>
  </div>
</template>
