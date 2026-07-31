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
import JsonEditorField from './JsonEditorField.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

const props = defineProps<{
  config: any
  providers: any[]
  variableGroups: WorkflowVariableGroup[]
  buffers: Record<string, string>
  errors: Record<string, string>
}>()
const emit = defineEmits<{
  structured: [payload: { field: string; buffer: string }]
  editing: [value: boolean]
}>()
const { t } = useI18n()

props.config.messages ||= []
props.config.context ||= ''
props.config.vision = { enabled: false, variable: '', detail: 'high', ...(props.config.vision || {}) }
props.config.reasoning = { separate: false, ...(props.config.reasoning || {}) }
const inputCount = computed(() => 1 + props.config.messages.length + (props.config.vision.enabled ? 1 : 0))

function selectProvider() {
  const provider = props.providers.find(item => item.id === props.config.provider_id)
  if (!provider) return
  props.config.provider_name = provider.name
  props.config.model = provider.default_model
}
function addMessage(role = 'user') { props.config.messages.push({ role, content: '' }) }
function removeMessage(index: number) { props.config.messages.splice(index, 1) }
</script>

<template>
  <section class="mt-5">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.nodeParametersHint')" kind="parameters">
      <div class="space-y-4">
        <FormField :label="t('designer.model')" required compact>
          <Select v-model="config.provider_id" @change="selectProvider"><option value="">{{ t('designer.selectModelProvider') }}</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }} · {{ provider.default_model }}</option></Select>
        </FormField>
        <p v-if="!providers.length" class="resource-empty">{{ t('designer.noModels') }}</p>
        <FormField :label="t('designer.modelName')" compact><InputText v-model="config.model" placeholder="gpt-4.1-mini" /></FormField>

        <NodeSettingCard :title="t('designer.vision')" :hint="t('designer.visionHint')" divided>
          <template #actions><ToggleSwitch v-model="config.vision.enabled" :label="t('designer.vision')" /></template>
          <FormField v-if="config.vision.enabled" :label="t('designer.visionResolution')" compact><Select v-model="config.vision.detail"><option value="auto">{{ t('designer.visionDetails.auto') }}</option><option value="high">{{ t('designer.visionDetails.high') }}</option><option value="low">{{ t('designer.visionDetails.low') }}</option></Select></FormField>
        </NodeSettingCard>

        <NodeSettingCard :title="t('designer.separateReasoning')" :hint="t('designer.separateReasoningHint')">
          <template #actions><ToggleSwitch v-model="config.reasoning.separate" :label="t('designer.separateReasoning')" /></template>
        </NodeSettingCard>

        <NodeConfigSection class="border-t border-[var(--border)] pt-4" :title="t('designer.modelParameters')" collapsible :default-expanded="false">
          <div class="space-y-4">
            <FormField :label="t('designer.temperature')" compact><div class="mt-1 flex items-center gap-3"><input v-model.number="config.temperature" class="min-w-0 flex-1 accent-[var(--primary)]" type="range" min="0" max="2" step="0.1"><InputText v-model.number="config.temperature" class="!w-20" type="number" min="0" max="2" step="0.1" /></div></FormField>
            <FormField label="Top P" compact><div class="mt-1 flex items-center gap-3"><input v-model.number="config.top_p" class="min-w-0 flex-1 accent-[var(--primary)]" type="range" min="0" max="1" step="0.05"><InputText v-model.number="config.top_p" class="!w-20" type="number" min="0" max="1" step="0.05" /></div></FormField>
            <FormField :label="t('designer.maxTokens')" compact><InputText v-model.number="config.max_tokens" type="number" min="1" max="128000" /></FormField>
          </div>
        </NodeConfigSection>

        <NodeConfigSection class="border-t border-[var(--border)] pt-4" :title="t('designer.structuredOutput')" :hint="t('designer.structuredOutputHint')">
          <Select v-model="config.response_format"><option value="text">{{ t('designer.responseFormats.text') }}</option><option value="json_object">{{ t('designer.responseFormats.json_object') }}</option><option value="json_schema">{{ t('designer.responseFormats.json_schema') }}</option></Select>
          <JsonEditorField v-if="config.response_format === 'json_schema'" :model-value="buffers.llmSchema" class="mt-3" label="JSON Schema" :error="errors.llmSchema" height-class="h-48" @focus="emit('editing', true)" @blur="emit('editing', false)" @update:model-value="buffers.llmSchema = $event" @input="emit('structured', { field: 'response_schema', buffer: 'llmSchema' })" />
        </NodeConfigSection>
      </div>
    </NodeConfigSection>

    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.inputVariables')" :hint="t('designer.inputVariablesHint')" :count="inputCount" kind="input" collapsible>
      <div class="space-y-3">
        <NodeSettingCard :title="t('designer.llmContext')" :hint="t('designer.llmContextHint')" type="String">
          <VariableField v-model="config.context" :groups="variableGroups" placeholder="{{SourceNode.text}}" />
        </NodeSettingCard>

        <div class="border-t border-[var(--border)] pt-4">
          <div class="flex items-start gap-3"><div class="min-w-0 flex-1"><h4 class="text-[11px] font-semibold">{{ t('designer.promptMessages') }}</h4><p class="muted mt-1 text-[10px] leading-4">{{ t('designer.promptMessagesHint') }}</p></div><IconButton :label="t('designer.addMessage')" size="sm" @click="addMessage()"><Plus :size="14" /></IconButton></div>
          <div class="mt-3 space-y-2">
            <NodeSettingCard v-for="(message, index) in config.messages" :key="index">
              <template #header><div class="flex min-w-0 flex-1 items-center gap-2"><Select v-model="message.role" class="!w-36 font-semibold"><option v-for="role in ['system','user','assistant']" :key="role" :value="role">{{ t(`designer.messageRoles.${role}`) }}</option></Select><span class="muted text-[10px]">#{{ Number(index) + 1 }}</span></div></template>
              <template #actions><IconButton :label="t('designer.removeMessage')" tone="danger" size="sm" @click="removeMessage(Number(index))"><Trash2 :size="13" /></IconButton></template>
              <VariableField v-model="message.content" :groups="variableGroups" multiline :rows="5" :placeholder="t('designer.promptPlaceholder')" />
            </NodeSettingCard>
            <button v-if="!config.messages.length" type="button" class="w-full rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addMessage()"><Plus class="mr-1 inline" :size="13" />{{ t('designer.addMessage') }}</button>
          </div>
        </div>

        <NodeSettingCard v-if="config.vision.enabled" :title="t('designer.imageVariable')" type="File">
          <VariableField v-model="config.vision.variable" class="font-mono" :groups="variableGroups" :placeholder="t('designer.variableReferencePlaceholder')" />
        </NodeSettingCard>
      </div>
    </NodeConfigSection>
  </section>
</template>
