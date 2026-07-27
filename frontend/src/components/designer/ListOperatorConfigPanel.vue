<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeConfigSection from './NodeConfigSection.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

function normalize() {
  const legacy = props.config.operation
  props.config.filter ||= { enabled: legacy === 'filter' && Boolean(props.config.expression), field: '', operator: 'equals', value: props.config.expression || '' }
  props.config.nth ||= { enabled: false, index: 1 }
  props.config.limit ||= { enabled: legacy === 'slice', count: legacy === 'slice' ? Math.max(0, Number(props.config.end || 10) - Number(props.config.start || 0)) : 10 }
  props.config.sort ||= { enabled: legacy === 'sort', order: 'asc', key: '' }
  if (typeof props.config.unique !== 'boolean') props.config.unique = legacy === 'unique'
}
normalize()
</script>

<template>
  <div data-testid="list-operator-config-panel" class="mt-5 space-y-5">
    <NodeConfigSection :title="t('designer.listSource')" :hint="t('designer.listSourceHint')"><VariableField v-model="config.source" class="font-mono" :groups="variableGroups" :placeholder="t('designer.selectArrayVariable')" /></NodeConfigSection>
    <NodeConfigSection :title="t('designer.listOperationsTitle')" :hint="t('designer.listOperationsHint')">
      <div class="space-y-2">
        <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3"><div class="flex items-center"><span class="text-xs font-semibold">{{ t('designer.listFilter') }}</span><ToggleSwitch v-model="config.filter.enabled" class="ml-auto" :label="t('designer.listFilter')" /></div><div v-if="config.filter.enabled" class="mt-3 grid grid-cols-[minmax(0,1fr)_112px] gap-2"><InputText v-model="config.filter.field" class="!h-9 font-mono !text-xs" :placeholder="t('designer.listFilterField')" /><Select v-model="config.filter.operator" class="!h-9 !text-xs"><option v-for="operator in ['equals','not_equals','contains','not_contains','greater_than','less_than','is_empty','is_not_empty']" :key="operator" :value="operator">{{ t(`designer.conditionOperators.${operator}`) }}</option></Select><VariableField v-if="!['is_empty','is_not_empty'].includes(config.filter.operator)" v-model="config.filter.value" class="col-span-2 font-mono" :groups="variableGroups" :placeholder="t('designer.listFilterValue')" /></div></section>
        <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3"><div class="flex items-center"><span class="text-xs font-semibold">{{ t('designer.listNth') }}</span><ToggleSwitch v-model="config.nth.enabled" class="ml-auto" :label="t('designer.listNth')" /></div><label v-if="config.nth.enabled" class="field-label mt-3">{{ t('designer.listNthIndex') }}<InputText v-model.number="config.nth.index" class="mt-1.5" type="number" min="1" /></label></section>
        <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3"><div class="flex items-center"><span class="text-xs font-semibold">{{ t('designer.listLimit') }}</span><ToggleSwitch v-model="config.limit.enabled" class="ml-auto" :label="t('designer.listLimit')" /></div><label v-if="config.limit.enabled" class="field-label mt-3">{{ t('designer.listLimitCount') }}<InputText v-model.number="config.limit.count" class="mt-1.5" type="number" min="0" /></label></section>
        <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3"><div class="flex items-center"><span class="text-xs font-semibold">{{ t('designer.listSort') }}</span><ToggleSwitch v-model="config.sort.enabled" class="ml-auto" :label="t('designer.listSort')" /></div><div v-if="config.sort.enabled" class="mt-3 grid grid-cols-[minmax(0,1fr)_112px] gap-2"><InputText v-model="config.sort.key" class="!h-9 font-mono !text-xs" :placeholder="t('designer.listSortKey')" /><Select v-model="config.sort.order" class="!h-9 !text-xs"><option value="asc">{{ t('designer.ascending') }}</option><option value="desc">{{ t('designer.descending') }}</option></Select></div></section>
        <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3"><div class="flex items-center"><div><div class="text-xs font-semibold">{{ t('designer.listUnique') }}</div><p class="muted mt-1 text-[10px]">{{ t('designer.listUniqueHint') }}</p></div><ToggleSwitch v-model="config.unique" class="ml-auto" :label="t('designer.listUnique')" /></div></section>
      </div>
    </NodeConfigSection>
  </div>
</template>
