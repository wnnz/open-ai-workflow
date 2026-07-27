<script setup lang="ts">
import { computed, ref } from 'vue'
import { BrainCircuit, Braces, Database, Globe2, Plus, Trash2, Wrench } from 'lucide-vue-next'
import VariableField from '@/components/VariableField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'

const props = defineProps<{ config: any; providers: any[]; scripts: any[]; datasets: any[]; variableGroups: any[] }>()
const emit = defineEmits<{ providerChange: [] }>()
const candidate = ref('')

function ensureConfig() {
  props.config.strategy ||= 'tool_calling'
  if (typeof props.config.query !== 'string') props.config.query = ''
  props.config.tools = Array.isArray(props.config.tools) ? props.config.tools : []
  props.config.memory = { enabled: false, window: 10, ...(props.config.memory || {}) }
  if (props.config.return_intermediate_steps == null) props.config.return_intermediate_steps = false
}
ensureConfig()

const candidates = computed(() => [
  { key: 'http:builtin', type: 'http', id: 'builtin', name: 'HTTP Request' },
  ...props.scripts.map(item => ({ key: `script:${item.id}`, type: 'script', id: item.id, name: item.name })),
  ...props.datasets.map(item => ({ key: `knowledge:${item.id}`, type: 'knowledge', id: item.id, name: item.name })),
])

function addTool() {
  const item = candidates.value.find(value => value.key === candidate.value)
  if (!item || props.config.tools.some((tool: any) => tool.type === item.type && tool.reference_id === item.id)) return
  props.config.tools.push({ id: crypto.randomUUID().slice(0, 12), type: item.type, reference_id: item.id, name: item.name, enabled: true, description: '' })
  candidate.value = ''
}
function removeTool(id: string) { props.config.tools = props.config.tools.filter((tool: any) => tool.id !== id) }
function toolIcon(type: string) { return type === 'script' ? Braces : type === 'knowledge' ? Database : Globe2 }
</script>

<template>
  <section class="mt-5 space-y-5">
    <div>
      <div class="flex items-center gap-2 text-xs font-semibold"><BrainCircuit :size="14" class="text-[var(--primary)]" />{{ $t('designer.agentStrategy') }}</div>
      <div class="mt-2 grid grid-cols-2 gap-2">
        <button v-for="strategy in ['tool_calling','react']" :key="strategy" type="button" class="rounded-lg border p-3 text-left" :class="config.strategy === strategy ? 'border-[var(--primary)] bg-[var(--primary-soft)]' : 'border-[var(--border)] hover:bg-[var(--panel-subtle)]'" @click="config.strategy = strategy">
          <span class="block text-xs font-semibold" :class="config.strategy === strategy && 'text-[var(--primary)]'">{{ $t(`designer.agentStrategies.${strategy}`) }}</span>
          <span class="muted mt-1 block text-[9px] leading-4">{{ $t(`designer.agentStrategyHints.${strategy}`) }}</span>
        </button>
      </div>
    </div>

    <label class="field-label">{{ $t('designer.modelProvider') }}<Select v-model="config.provider_id" class="mt-1.5 !h-9 !text-xs" @change="emit('providerChange')"><option value="">{{ $t('designer.selectModelProvider') }}</option><option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }} · {{ provider.default_model }}</option></Select></label>
    <p v-if="!providers.length" class="resource-empty">{{ $t('designer.noModels') }}</p>
    <label class="field-label">{{ $t('designer.modelName') }}<InputText v-model="config.model" class="mt-1.5" placeholder="gpt-4.1-mini" /></label>
    <label class="field-label">{{ $t('designer.agentInstructions') }}<VariableField v-model="config.instructions" class="mt-1.5" :groups="variableGroups" multiline :rows="7" :placeholder="$t('designer.agentInstructionsPlaceholder')" /></label>
    <label class="field-label">{{ $t('designer.agentQuery') }}<VariableField v-model="config.query" class="mt-1.5" :groups="variableGroups" :placeholder="$t('designer.agentQueryPlaceholder')" /></label>

    <div>
      <div class="flex items-center gap-2"><Wrench :size="14" class="text-[var(--primary)]" /><h3 class="text-xs font-semibold">{{ $t('designer.agentTools') }}</h3><span class="muted ml-auto text-[10px]">{{ config.tools.length }}</span></div>
      <p class="muted mt-1 text-[10px] leading-4">{{ $t('designer.agentToolsHint') }}</p>
      <div class="mt-2 flex gap-2"><Select v-model="candidate" class="min-w-0 flex-1 !h-9 !text-xs"><option value="">{{ $t('designer.selectAgentTool') }}</option><option v-for="item in candidates" :key="item.key" :value="item.key">{{ item.name }} · {{ $t(`designer.agentToolTypes.${item.type}`) }}</option></Select><button type="button" class="icon-button surface !h-9 !w-9" :disabled="!candidate" :aria-label="$t('designer.addAgentTool')" @click="addTool"><Plus :size="14" /></button></div>
      <div class="mt-2 space-y-2">
        <div v-for="tool in config.tools" :key="tool.id" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-2.5">
          <div class="flex items-center gap-2"><span class="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--panel)] text-[var(--primary)]"><component :is="toolIcon(tool.type)" :size="14" /></span><span class="min-w-0 flex-1 truncate text-xs font-semibold">{{ tool.name }}</span><label class="flex items-center gap-1 text-[9px] text-[var(--muted)]"><input v-model="tool.enabled" type="checkbox" />{{ $t('designer.enabled') }}</label><button type="button" class="icon-button !h-7 !w-7 text-red-600" :aria-label="$t('common.delete')" @click="removeTool(tool.id)"><Trash2 :size="12" /></button></div>
          <InputText v-model="tool.description" class="mt-2 !h-8 !text-[10px]" :placeholder="$t('designer.agentToolDescription')" />
        </div>
        <div v-if="!config.tools.length" class="resource-empty text-center">{{ $t('designer.noAgentTools') }}</div>
      </div>
    </div>

    <div class="grid grid-cols-2 gap-3"><label class="field-label">{{ $t('designer.maxIterations') }}<InputText :model-value="String(config.max_iterations)" class="mt-1.5" type="number" min="1" max="50" @update:model-value="config.max_iterations = Number($event)" /></label><label class="field-label">{{ $t('designer.memoryWindow') }}<InputText :model-value="String(config.memory.window)" class="mt-1.5" type="number" min="1" max="100" :disabled="!config.memory.enabled" @update:model-value="config.memory.window = Number($event)" /></label></div>
    <label class="flex items-start gap-2 rounded-lg border border-[var(--border)] p-3 text-xs"><input v-model="config.memory.enabled" class="mt-0.5" type="checkbox" /><span><span class="block font-semibold">{{ $t('designer.enableAgentMemory') }}</span><span class="muted mt-1 block text-[10px]">{{ $t('designer.enableAgentMemoryHint') }}</span></span></label>
    <label class="flex items-start gap-2 rounded-lg border border-[var(--border)] p-3 text-xs"><input v-model="config.return_intermediate_steps" class="mt-0.5" type="checkbox" /><span><span class="block font-semibold">{{ $t('designer.returnIntermediateSteps') }}</span><span class="muted mt-1 block text-[10px]">{{ $t('designer.returnIntermediateStepsHint') }}</span></span></label>
  </section>
</template>
