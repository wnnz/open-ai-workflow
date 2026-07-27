<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeConfigSection from './NodeConfigSection.vue'

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
</script>

<template>
  <div data-testid="parameter-extractor-config-panel" class="mt-5 space-y-5">
    <NodeConfigSection :title="t('designer.model')" :hint="t('designer.extractModelHint')">
      <Select v-model="config.provider_id" class="!h-9 !text-xs" @change="selectProvider"><option value="">{{ t('designer.selectModelProvider') }}</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }} · {{ provider.default_model }}</option></Select>
      <InputText v-model="config.model" class="mt-2 !h-9" :placeholder="t('designer.modelName')" />
      <p v-if="!providers.length" class="resource-empty mt-2">{{ t('designer.noModels') }}</p>
    </NodeConfigSection>

    <NodeConfigSection :title="t('designer.extractInput')" :hint="t('designer.extractInputHint')">
      <VariableField v-model="config.source" class="font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" />
    </NodeConfigSection>

    <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
      <div class="flex items-center gap-3"><div class="min-w-0 flex-1"><h3 class="text-xs font-semibold">{{ t('designer.vision') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.extractVisionHint') }}</p></div><ToggleSwitch v-model="config.vision.enabled" :label="t('designer.vision')" /></div>
      <VariableField v-if="config.vision.enabled" v-model="config.vision.variable" class="mt-3 font-mono" :groups="variableGroups" :placeholder="t('designer.selectImageVariable')" />
    </section>

    <NodeConfigSection :title="t('designer.extractFields')" :hint="t('designer.extractFieldsHint')">
      <template #actions><IconButton :label="t('designer.addExtractField')" size="sm" @click="addField"><Plus :size="14" /></IconButton></template>
      <div class="space-y-3">
        <div v-for="(field, index) in config.fields" :key="index" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
          <div class="grid grid-cols-[minmax(0,1fr)_92px_28px] gap-2"><InputText v-model="field.name" class="!h-9 font-mono !text-xs" placeholder="field_name" /><Select v-model="field.type" class="!h-9 !text-xs"><option v-for="type in ['String','Number','Boolean','Object','Array']" :key="type" :value="type">{{ type }}</option></Select><IconButton :label="t('designer.removeExtractField')" tone="danger" size="sm" @click="config.fields.splice(Number(index), 1)"><Trash2 :size="13" /></IconButton></div>
          <InputText v-model="field.description" class="mt-2 !h-9" :placeholder="t('designer.fieldDescription')" />
          <label class="mt-2 flex items-center gap-2 text-[11px]"><input v-model="field.required" type="checkbox" class="accent-[var(--primary)]" />{{ t('designer.requiredForExtraction') }}</label>
        </div>
        <button v-if="!config.fields.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addField"><Plus :size="14" />{{ t('designer.addExtractField') }}</button>
      </div>
    </NodeConfigSection>

    <NodeConfigSection :title="t('designer.extractionInstruction')" :hint="t('designer.extractionInstructionHint')">
      <VariableField v-model="config.instruction" :groups="variableGroups" multiline :rows="5" :placeholder="t('designer.extractionInstructionPlaceholder')" />
    </NodeConfigSection>
  </div>
</template>
