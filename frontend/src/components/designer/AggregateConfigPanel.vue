<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

if (!Array.isArray(props.config.variables)) props.config.variables = []
if (!Array.isArray(props.config.groups)) props.config.groups = []
if (typeof props.config.group_enabled !== 'boolean') props.config.group_enabled = false

function addVariable(target: any[]) { target.push('') }
function removeVariable(target: any[], index: number) { target.splice(index, 1) }
function addGroup() {
  const index = props.config.groups.length + 1
  props.config.groups.push({ name: `group${index}`, variables: [''] })
}
function removeGroup(index: number) { props.config.groups.splice(index, 1) }
function enableGroups(value: boolean) {
  props.config.group_enabled = value
  if (value && !props.config.groups.length) addGroup()
}
const inputCount = computed(() => props.config.group_enabled
  ? props.config.groups.reduce((total: number, group: any) => total + (group.variables?.length || 0), 0)
  : props.config.variables.length)
</script>

<template>
  <div data-testid="aggregate-config-panel" class="mt-5">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.nodeParametersHint')" kind="parameters">
      <NodeSettingCard :title="t('designer.aggregateGrouping')" :hint="t('designer.aggregateGroupingHint')"><template #actions><ToggleSwitch :model-value="config.group_enabled" :label="t('designer.aggregateGrouping')" @update:model-value="enableGroups" /></template></NodeSettingCard>
    </NodeConfigSection>

    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.inputVariables')" :hint="config.group_enabled ? t('designer.aggregateGroupsHint') : t('designer.aggregateHint')" :count="inputCount" kind="input" collapsible>
      <template #actions><IconButton :label="config.group_enabled ? t('designer.addAggregateGroup') : t('designer.addAggregateVariable')" size="sm" @click="config.group_enabled ? addGroup() : addVariable(config.variables)"><Plus :size="14" /></IconButton></template>
      <div v-if="!config.group_enabled" class="space-y-2">
        <NodeSettingCard v-for="(_, index) in config.variables" :key="index"><div class="flex gap-2"><VariableField v-model="config.variables[index]" class="min-w-0 flex-1 font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" /><IconButton :label="t('designer.removeAggregateVariable')" tone="danger" @click="removeVariable(config.variables, Number(index))"><Trash2 :size="13" /></IconButton></div></NodeSettingCard>
        <button v-if="!config.variables.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-4 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addVariable(config.variables)"><Plus :size="14" />{{ t('designer.addAggregateVariable') }}</button>
      </div>
      <div v-else class="space-y-3">
        <NodeSettingCard v-for="(group, groupIndex) in config.groups" :key="groupIndex">
          <div class="flex items-center gap-2"><InputText v-model="group.name" class="min-w-0 flex-1 font-mono" placeholder="group1" /><IconButton :label="t('designer.removeAggregateGroup')" tone="danger" size="sm" @click="removeGroup(Number(groupIndex))"><Trash2 :size="13" /></IconButton></div>
          <div class="mt-3 space-y-2"><div v-for="(_, variableIndex) in group.variables" :key="variableIndex" class="flex gap-2"><VariableField v-model="group.variables[variableIndex]" class="min-w-0 flex-1 font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" /><IconButton :label="t('designer.removeAggregateVariable')" tone="danger" size="sm" @click="removeVariable(group.variables, Number(variableIndex))"><Trash2 :size="12" /></IconButton></div><button type="button" class="flex items-center gap-1.5 text-[11px] font-semibold text-[var(--primary)]" @click="addVariable(group.variables)"><Plus :size="12" />{{ t('designer.addAggregateVariable') }}</button></div>
        </NodeSettingCard>
      </div>
    </NodeConfigSection>
  </div>
</template>
