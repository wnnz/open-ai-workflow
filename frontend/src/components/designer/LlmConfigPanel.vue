<script setup lang="ts">
import { Plus, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import JsonEditorField from './JsonEditorField.vue'
import NodeInputPanel from './NodeInputPanel.vue'

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
  <section class="mt-5 space-y-5">
    <div>
      <h3 class="text-xs font-semibold">{{ t('designer.model') }} <span class="text-red-500">*</span></h3>
      <Select v-model="config.provider_id" class="mt-2 !h-9 !text-xs" @change="selectProvider"><option value="">{{ t('designer.selectModelProvider') }}</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }} · {{ provider.default_model }}</option></Select>
      <p v-if="!providers.length" class="resource-empty mt-2">{{ t('designer.noModels') }}</p>
      <label class="field-label mt-3">{{ t('designer.modelName') }}<InputText v-model="config.model" class="mt-1.5" placeholder="gpt-4.1-mini" /></label>
    </div>

    <NodeInputPanel :config="config" :fields="[{ key: 'context', label: t('designer.llmContext'), type: 'String', placeholder: '{{knowledge.documents}}', hint: t('designer.llmContextHint') }]" :variable-groups="variableGroups" />

    <div>
      <div class="flex items-center"><div><h3 class="text-xs font-semibold">{{ t('designer.promptMessages') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.promptMessagesHint') }}</p></div><button type="button" class="icon-button ml-auto" :aria-label="t('designer.addMessage')" @click="addMessage()"><Plus :size="14" /></button></div>
      <div class="mt-3 space-y-2">
        <div v-for="(message, index) in config.messages" :key="index" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
          <div class="mb-2 flex items-center gap-2"><Select v-model="message.role" class="!h-8 !w-32 !text-xs font-semibold"><option v-for="role in ['system','user','assistant']" :key="role" :value="role">{{ t(`designer.messageRoles.${role}`) }}</option></Select><span class="muted text-[10px]">#{{ Number(index) + 1 }}</span><button type="button" class="icon-button ml-auto text-red-600" :aria-label="t('designer.removeMessage')" @click="removeMessage(Number(index))"><Trash2 :size="13" /></button></div>
          <VariableField v-model="message.content" :groups="variableGroups" multiline :rows="5" :placeholder="t('designer.promptPlaceholder')" />
        </div>
        <button v-if="!config.messages.length" type="button" class="w-full rounded-lg border border-dashed border-[var(--border)] py-5 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addMessage()"><Plus class="mr-1 inline" :size="13" />{{ t('designer.addMessage') }}</button>
      </div>
    </div>

    <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
      <div class="flex items-center gap-3"><div class="min-w-0 flex-1"><h3 class="text-xs font-semibold">{{ t('designer.vision') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.visionHint') }}</p></div><ToggleSwitch v-model="config.vision.enabled" :label="t('designer.vision')" /></div>
      <div v-if="config.vision.enabled" class="mt-3 space-y-3 border-t border-[var(--border)] pt-3">
        <label class="field-label">{{ t('designer.imageVariable') }}<VariableField v-model="config.vision.variable" class="mt-1.5 font-mono" :groups="variableGroups" :placeholder="t('designer.variableReferencePlaceholder')" /></label>
        <label class="field-label">{{ t('designer.visionResolution') }}<Select v-model="config.vision.detail" class="mt-1.5 !h-9 !text-xs"><option value="auto">{{ t('designer.visionDetails.auto') }}</option><option value="high">{{ t('designer.visionDetails.high') }}</option><option value="low">{{ t('designer.visionDetails.low') }}</option></Select></label>
      </div>
    </section>

    <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3"><div class="flex items-center gap-3"><div class="min-w-0 flex-1"><h3 class="text-xs font-semibold">{{ t('designer.separateReasoning') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.separateReasoningHint') }}</p></div><ToggleSwitch v-model="config.reasoning.separate" :label="t('designer.separateReasoning')" /></div></section>

    <details class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]" open><summary class="cursor-pointer px-3 py-2.5 text-xs font-semibold">{{ t('designer.modelParameters') }}</summary><div class="space-y-4 border-t border-[var(--border)] p-3"><label class="field-label">{{ t('designer.temperature') }}<div class="mt-2 flex items-center gap-3"><input v-model.number="config.temperature" class="min-w-0 flex-1 accent-[var(--primary)]" type="range" min="0" max="2" step="0.1"><InputText v-model.number="config.temperature" class="!w-20" type="number" min="0" max="2" step="0.1" /></div></label><label class="field-label">Top P<div class="mt-2 flex items-center gap-3"><input v-model.number="config.top_p" class="min-w-0 flex-1 accent-[var(--primary)]" type="range" min="0" max="1" step="0.05"><InputText v-model.number="config.top_p" class="!w-20" type="number" min="0" max="1" step="0.05" /></div></label><label class="field-label">{{ t('designer.maxTokens') }}<InputText v-model.number="config.max_tokens" class="mt-1.5" type="number" min="1" max="128000" /></label></div></details>

    <section>
      <h3 class="text-xs font-semibold">{{ t('designer.structuredOutput') }}</h3><p class="muted mt-1 text-[11px]">{{ t('designer.structuredOutputHint') }}</p>
      <Select v-model="config.response_format" class="mt-2 !h-9 !text-xs"><option value="text">{{ t('designer.responseFormats.text') }}</option><option value="json_object">{{ t('designer.responseFormats.json_object') }}</option><option value="json_schema">{{ t('designer.responseFormats.json_schema') }}</option></Select>
      <JsonEditorField v-if="config.response_format === 'json_schema'" :model-value="buffers.llmSchema" class="mt-3" label="JSON Schema" :error="errors.llmSchema" height-class="h-48" @focus="emit('editing', true)" @blur="emit('editing', false)" @update:model-value="buffers.llmSchema = $event" @input="emit('structured', { field: 'response_schema', buffer: 'llmSchema' })" />
    </section>
  </section>
</template>
