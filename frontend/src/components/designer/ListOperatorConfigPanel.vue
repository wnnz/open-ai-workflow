<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

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
  <div data-testid="list-operator-config-panel" class="mt-5">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.nodeParametersHint')" kind="parameters">
      <NodeConfigSection :title="t('designer.listOperationsTitle')" :hint="t('designer.listOperationsHint')">
        <div class="space-y-2">
          <NodeSettingCard :title="t('designer.listFilter')" divided><template #actions><ToggleSwitch v-model="config.filter.enabled" :label="t('designer.listFilter')" /></template><div v-if="config.filter.enabled" class="grid grid-cols-[minmax(0,1fr)_112px] gap-2"><InputText v-model="config.filter.field" class="font-mono" :placeholder="t('designer.listFilterField')" /><Select v-model="config.filter.operator"><option v-for="operator in ['equals','not_equals','contains','not_contains','greater_than','less_than','is_empty','is_not_empty']" :key="operator" :value="operator">{{ t(`designer.conditionOperators.${operator}`) }}</option></Select><VariableField v-if="!['is_empty','is_not_empty'].includes(config.filter.operator)" v-model="config.filter.value" class="col-span-2 font-mono" :groups="variableGroups" :placeholder="t('designer.listFilterValue')" /></div></NodeSettingCard>
          <NodeSettingCard :title="t('designer.listNth')" divided><template #actions><ToggleSwitch v-model="config.nth.enabled" :label="t('designer.listNth')" /></template><label v-if="config.nth.enabled" class="field-label">{{ t('designer.listNthIndex') }}<InputText v-model.number="config.nth.index" class="mt-1.5" type="number" min="1" /></label></NodeSettingCard>
          <NodeSettingCard :title="t('designer.listLimit')" divided><template #actions><ToggleSwitch v-model="config.limit.enabled" :label="t('designer.listLimit')" /></template><label v-if="config.limit.enabled" class="field-label">{{ t('designer.listLimitCount') }}<InputText v-model.number="config.limit.count" class="mt-1.5" type="number" min="0" /></label></NodeSettingCard>
          <NodeSettingCard :title="t('designer.listSort')" divided><template #actions><ToggleSwitch v-model="config.sort.enabled" :label="t('designer.listSort')" /></template><div v-if="config.sort.enabled" class="grid grid-cols-[minmax(0,1fr)_112px] gap-2"><InputText v-model="config.sort.key" class="font-mono" :placeholder="t('designer.listSortKey')" /><Select v-model="config.sort.order"><option value="asc">{{ t('designer.ascending') }}</option><option value="desc">{{ t('designer.descending') }}</option></Select></div></NodeSettingCard>
          <NodeSettingCard :title="t('designer.listUnique')" :hint="t('designer.listUniqueHint')"><template #actions><ToggleSwitch v-model="config.unique" :label="t('designer.listUnique')" /></template></NodeSettingCard>
        </div>
      </NodeConfigSection>
    </NodeConfigSection>
    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.inputVariables')" :hint="t('designer.listSourceHint')" :count="1" kind="input" collapsible><NodeSettingCard :title="t('designer.listSource')" type="Array"><VariableField v-model="config.source" class="font-mono" :groups="variableGroups" :placeholder="t('designer.selectArrayVariable')" /></NodeSettingCard></NodeConfigSection>
  </div>
</template>
