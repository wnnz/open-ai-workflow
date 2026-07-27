<script setup lang="ts">
import { Plus, ShieldCheck, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import CodeEditor from '@/components/CodeEditor.vue'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import NodeConfigSection from './NodeConfigSection.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const emit = defineEmits<{ editing: [value: boolean] }>()
const { t } = useI18n()

if (!Array.isArray(props.config.inputs)) props.config.inputs = []
if (!Array.isArray(props.config.outputs)) props.config.outputs = []
props.config.entrypoint ||= 'main'
props.config.timeout_seconds ||= 30
props.config.memory_mb ||= 256
if (typeof props.config.network_enabled !== 'boolean') props.config.network_enabled = false

function nextName(prefix: string, items: any[]) {
  let index = items.length + 1
  const names = new Set(items.map(item => item?.name))
  while (names.has(`${prefix}${index}`)) index += 1
  return `${prefix}${index}`
}
function addInput() { props.config.inputs.push({ name: nextName('arg', props.config.inputs), type: 'Any', value: '' }) }
function addOutput() { props.config.outputs.push({ name: nextName('result', props.config.outputs), type: 'Any' }) }
</script>

<template>
  <div data-testid="code-config-panel" class="mt-5 space-y-5">
    <NodeConfigSection :title="t('designer.codeInputs')" :hint="t('designer.codeInputsHint')">
      <template #actions><IconButton :label="t('designer.addCodeInput')" size="sm" @click="addInput"><Plus :size="14" /></IconButton></template>
      <div class="space-y-2">
        <div v-for="(input, index) in config.inputs" :key="index" class="grid grid-cols-[88px_78px_minmax(0,1fr)_28px] gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-2">
          <InputText v-model="input.name" class="!h-9 font-mono !text-xs" placeholder="arg1" />
          <Select v-model="input.type" class="!h-9 !px-2 !text-[10px]"><option v-for="type in ['String','Number','Boolean','Object','Array','Any']" :key="type" :value="type">{{ type }}</option></Select>
          <VariableField v-model="input.value" class="min-w-0 font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" />
          <IconButton :label="t('designer.removeCodeInput')" tone="danger" size="sm" @click="config.inputs.splice(Number(index), 1)"><Trash2 :size="13" /></IconButton>
        </div>
        <button v-if="!config.inputs.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-4 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addInput"><Plus :size="14" />{{ t('designer.addCodeInput') }}</button>
      </div>
    </NodeConfigSection>

    <NodeConfigSection :title="t('designer.pythonCode')" :hint="t('designer.pythonCodeHint')">
      <CodeEditor v-model="config.source" language="python" height="360px" @focus="emit('editing', true)" @blur="emit('editing', false)" />
    </NodeConfigSection>

    <NodeConfigSection :title="t('designer.codeOutputs')" :hint="t('designer.codeOutputsHint')">
      <template #actions><IconButton :label="t('designer.addCodeOutput')" size="sm" @click="addOutput"><Plus :size="14" /></IconButton></template>
      <div class="space-y-2"><div v-for="(output, index) in config.outputs" :key="index" class="grid grid-cols-[minmax(0,1fr)_100px_28px] gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-2"><InputText v-model="output.name" class="!h-9 font-mono !text-xs" placeholder="result" /><Select v-model="output.type" class="!h-9 !text-xs"><option v-for="type in ['String','Number','Boolean','Object','Array','File','Any']" :key="type" :value="type">{{ type }}</option></Select><IconButton :label="t('designer.removeCodeOutput')" tone="danger" size="sm" @click="config.outputs.splice(Number(index), 1)"><Trash2 :size="13" /></IconButton></div></div>
    </NodeConfigSection>

    <details class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]"><summary class="cursor-pointer px-3 py-2.5 text-xs font-semibold">{{ t('designer.codeRuntime') }}</summary><div class="space-y-4 border-t border-[var(--border)] p-3"><label class="field-label">{{ t('designer.codeEntrypoint') }}<InputText v-model="config.entrypoint" class="mt-1.5 font-mono" /></label><div class="grid grid-cols-2 gap-3"><label class="field-label">{{ t('designer.timeoutSeconds') }}<InputText v-model.number="config.timeout_seconds" class="mt-1.5" type="number" min="1" max="300" /></label><label class="field-label">{{ t('designer.memoryMb') }}<InputText v-model.number="config.memory_mb" class="mt-1.5" type="number" min="64" max="2048" /></label></div><div class="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--panel)] p-3"><ShieldCheck :size="16" class="text-emerald-600" /><div class="min-w-0 flex-1"><div class="text-xs font-semibold">{{ t('designer.codeNetwork') }}</div><p class="muted mt-1 text-[10px]">{{ t('designer.codeNetworkHint') }}</p></div><ToggleSwitch v-model="config.network_enabled" :label="t('designer.codeNetwork')" /></div></div></details>
  </div>
</template>
