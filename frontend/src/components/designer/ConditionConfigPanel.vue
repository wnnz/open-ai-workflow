<script setup lang="ts">
import { Plus, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import VariableField from '@/components/VariableField.vue'
import IconButton from '@/volt/IconButton.vue'
import Select from '@/volt/Select.vue'
import BranchButton from './BranchButton.vue'
import NodeConfigSection from './NodeConfigSection.vue'

defineProps<{ config: any; variableGroups: WorkflowVariableGroup[] }>()
const emit = defineEmits<{ add: []; remove: [index: number]; connect: [handle: string] }>()
const { t } = useI18n()
const operators = ['equals','not_equals','contains','not_contains','starts_with','ends_with','greater_than','less_than','greater_or_equal','less_or_equal','is_empty','is_not_empty','in']
</script>

<template>
  <div class="mt-5">
    <NodeConfigSection :title="t('designer.conditionRules')" :hint="t('designer.conditionRulesHint')">
      <template #actions><IconButton :label="t('designer.addCondition')" size="sm" @click="emit('add')"><Plus :size="14" /></IconButton></template>
      <div v-if="config.conditions.length > 1" class="mb-3 flex rounded-md bg-[var(--panel-subtle)] p-1"><button v-for="logic in ['and','or']" :key="logic" type="button" class="flex-1 rounded px-2 py-1.5 text-[10px] font-semibold" :class="config.logical_operator === logic ? 'bg-[var(--panel)] text-[var(--primary)] shadow-sm' : 'text-[var(--muted)]'" @click="config.logical_operator = logic">{{ t(`designer.conditionLogic.${logic}`) }}</button></div>
      <div class="space-y-2">
        <article v-for="(clause, index) in config.conditions" :key="index" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
          <div class="mb-2 flex items-center text-[10px] font-semibold text-[var(--muted)]"><span class="flex h-5 w-5 items-center justify-center rounded bg-[var(--primary-soft)] text-[var(--primary)]">{{ Number(index) + 1 }}</span><span v-if="Number(index) > 0" class="ml-2">{{ t(`designer.conditionLogic.${config.logical_operator}`) }}</span><IconButton class="ml-auto" :label="t('designer.removeCondition')" tone="danger" size="sm" @click="emit('remove', Number(index))"><X :size="13" /></IconButton></div>
          <VariableField v-model="clause.variable" :groups="variableGroups" :placeholder="t('designer.selectConditionVariable')" />
          <Select v-model="clause.operator" class="mt-2 !h-8 !text-xs"><option v-for="operator in operators" :key="operator" :value="operator">{{ t(`designer.conditionOperators.${operator}`) }}</option></Select>
          <VariableField v-if="!['is_empty','is_not_empty'].includes(clause.operator)" v-model="clause.value" class="mt-2" :groups="variableGroups" :placeholder="t('designer.conditionValue')" />
        </article>
        <button v-if="!config.conditions.length" type="button" class="w-full rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="emit('add')"><Plus class="mr-1 inline" :size="13" />{{ t('designer.addCondition') }}</button>
      </div>
    </NodeConfigSection>
    <details v-if="config.expression" class="mt-3 rounded-lg border border-[var(--border)] p-3" open><summary class="cursor-pointer text-[11px] font-semibold">{{ t('designer.legacyCondition') }}</summary><VariableField v-model="config.expression" class="mt-3 font-mono" :groups="variableGroups" multiline :rows="4" :placeholder="t('designer.conditionPlaceholder')" /></details>
    <div class="mt-4 grid grid-cols-2 gap-2"><BranchButton :label="`IF · ${t('designer.trueBranch')}`" tone="success" @click="emit('connect', 'true')" /><BranchButton :label="`ELSE · ${t('designer.falseBranch')}`" tone="warning" @click="emit('connect', 'false')" /></div>
  </div>
</template>
