<script setup lang="ts">
import { computed, ref } from 'vue'
import { Braces, Plus, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import NodeConfigSection from './NodeConfigSection.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: WorkflowVariableGroup[] }>()
const { t } = useI18n()
const editor = ref<{ insertText: (text: string) => Promise<void> } | null>(null)

if (!Array.isArray(props.config.inputs)) props.config.inputs = []
if (typeof props.config.template !== 'string') props.config.template = ''

const usedNames = computed(() => new Set(props.config.inputs.map((item: any) => String(item?.name || ''))))

function addInput() {
  let index = props.config.inputs.length + 1
  while (usedNames.value.has(`arg${index}`)) index += 1
  props.config.inputs.push({ name: `arg${index}`, value: '' })
}

function removeInput(index: number) {
  props.config.inputs.splice(index, 1)
}

async function insertBinding(name: string) {
  if (!name) return
  await editor.value?.insertText(`{{ ${name} }}`)
}
</script>

<template>
  <div data-testid="template-config-panel" class="mt-5 space-y-5">
    <NodeConfigSection :title="t('designer.inputVariables')" :hint="t('designer.templateInputsHint')">
      <template #actions><IconButton :label="t('designer.addTemplateInput')" size="sm" @click="addInput"><Plus :size="14" /></IconButton></template>
      <div class="space-y-2">
        <div v-for="(input, index) in config.inputs" :key="index" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
          <div class="grid grid-cols-[minmax(72px,0.7fr)_minmax(0,1.3fr)_32px] items-center gap-2">
            <InputText v-model="input.name" class="!h-9 font-mono !text-xs" placeholder="arg1" />
            <VariableField v-model="input.value" class="min-w-0 font-mono" :groups="variableGroups" :placeholder="t('designer.selectUpstreamOutput')" />
            <IconButton class="self-center" :label="t('designer.removeTemplateInput')" tone="danger" size="sm" @click="removeInput(Number(index))"><Trash2 :size="13" /></IconButton>
          </div>
        </div>
        <button v-if="!config.inputs.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-4 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addInput"><Plus :size="14" />{{ t('designer.addTemplateInput') }}</button>
      </div>
    </NodeConfigSection>

    <NodeConfigSection :title="t('designer.templateContent')" :hint="t('designer.jinjaOnly')">
      <div v-if="config.inputs.length" class="mb-2 flex flex-wrap gap-1.5">
        <button v-for="input in config.inputs" :key="input.name" type="button" class="inline-flex items-center gap-1 rounded-md bg-[var(--primary-soft)] px-2 py-1 font-mono text-[10px] text-[var(--primary)]" @click="insertBinding(input.name)"><Braces :size="11" />{{ input.name || t('designer.unnamedVariable') }}</button>
      </div>
      <VariableField ref="editor" v-model="config.template" :groups="variableGroups" multiline :rows="12" :spellcheck="false" control-class="min-h-64 !bg-slate-950 !p-3 !pr-10 !font-mono !text-xs !leading-5 !text-slate-100" :placeholder="t('designer.templateJinjaPlaceholder')" />
    </NodeConfigSection>
  </div>
</template>
