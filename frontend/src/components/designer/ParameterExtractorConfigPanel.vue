<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

const props = defineProps<{ config: Record<string, any>; providers: any[]; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()

if (!Array.isArray(props.config.fields)) props.config.fields = []
props.config.vision = { enabled: false, variable: '', ...(props.config.vision || {}) }
if (typeof props.config.instruction !== 'string') props.config.instruction = ''
for (const field of props.config.fields) {
  field.type ||= 'String'
  field.required = Boolean(field.required)
}

function selectProvider() {
  const provider = props.providers.find(item => item.id === props.config.provider_id)
  if (!provider) return
  props.config.provider_name = provider.name
  props.config.model = provider.default_model
}
function addField() { props.config.fields.push({ name: '', type: 'String', description: '', required: false }) }
const inputCount = computed(() => 2 + (props.config.vision.enabled ? 1 : 0))
</script>

<template>
  <div data-testid="parameter-extractor-config-panel" class="mt-5">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.nodeParametersHint')" kind="parameters">
      <div class="space-y-4">
        <NodeConfigSection :title="t('designer.model')" :hint="t('designer.extractModelHint')">
          <FormField :label="t('designer.modelProvider')" required compact><Select v-model="config.provider_id" @change="selectProvider"><option value="">{{ t('designer.selectModelProvider') }}</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }} · {{ provider.default_model }}</option></Select></FormField>
          <FormField class="mt-3" :label="t('designer.modelName')" compact><InputText v-model="config.model" :placeholder="t('designer.modelName')" /></FormField>
          <p v-if="!providers.length" class="resource-empty mt-2">{{ t('designer.noModels') }}</p>
        </NodeConfigSection>
        <NodeSettingCard :title="t('designer.vision')" :hint="t('designer.extractVisionHint')"><template #actions><ToggleSwitch v-model="config.vision.enabled" :label="t('designer.vision')" /></template></NodeSettingCard>
        <NodeConfigSection class="border-t border-[var(--border)] pt-4" :title="t('designer.extractFields')" :hint="t('designer.extractFieldsHint')" :count="config.fields.length">
          <template #actions><IconButton :label="t('designer.addExtractField')" size="sm" @click="addField"><Plus :size="14" /></IconButton></template>
          <div class="space-y-3"><NodeSettingCard v-for="(field, index) in config.fields" :key="index"><div class="grid grid-cols-[minmax(0,1fr)_92px_28px] gap-2"><InputText v-model="field.name" class="font-mono" placeholder="field_name" /><Select v-model="field.type"><option v-for="type in ['String','Number','Boolean','Object','Array']" :key="type" :value="type">{{ type }}</option></Select><IconButton :label="t('designer.removeExtractField')" tone="danger" size="sm" @click="config.fields.splice(Number(index), 1)"><Trash2 :size="13" /></IconButton></div><InputText v-model="field.description" class="mt-2" :placeholder="t('designer.fieldDescription')" /><label class="mt-2 flex items-center gap-2 text-[11px]"><input v-model="field.required" type="checkbox" class="accent-[var(--primary)]" />{{ t('designer.requiredForExtraction') }}</label></NodeSettingCard><button v-if="!config.fields.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addField"><Plus :size="14" />{{ t('designer.addExtractField') }}</button></div>
        </NodeConfigSection>
      </div>
    </NodeConfigSection>

    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.inputVariables')" :hint="t('designer.inputVariablesHint')" :count="inputCount" kind="input" collapsible>
      <div class="space-y-3">
        <NodeSettingCard :title="t('designer.extractInput')" :hint="t('designer.extractInputHint')" type="String" required><VariableField v-model="config.source" class="font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" /></NodeSettingCard>
        <NodeSettingCard :title="t('designer.extractionInstruction')" :hint="t('designer.extractionInstructionHint')" type="String"><VariableField v-model="config.instruction" :groups="variableGroups" multiline :rows="5" :placeholder="t('designer.extractionInstructionPlaceholder')" /></NodeSettingCard>
        <NodeSettingCard v-if="config.vision.enabled" :title="t('designer.imageVariable')" type="File"><VariableField v-model="config.vision.variable" class="font-mono" :groups="variableGroups" :placeholder="t('designer.selectImageVariable')" /></NodeSettingCard>
      </div>
    </NodeConfigSection>
  </div>
</template>
