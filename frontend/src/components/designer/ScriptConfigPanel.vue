<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Braces } from 'lucide-vue-next'
import api from '@/api/client'
import VariableField from '@/components/VariableField.vue'
import Select from '@/volt/Select.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

const props = defineProps<{ config: Record<string, any>; scripts: any[]; workspaceId: string; variableGroups: WorkflowVariableGroup[] }>()
const versions = ref<any[]>([])
const runtime = ref<any>(null)
const loading = ref(false)
const selectedScript = computed(() => props.scripts.find(item => item.id === props.config.script_id))
const inputProperties = computed(() => runtime.value?.input_schema?.properties || {})
const outputProperties = computed(() => runtime.value?.output_schema?.properties || {})
const requiredInputs = computed(() => new Set<string>(runtime.value?.input_schema?.required || []))

async function loadRuntime() {
  const script = selectedScript.value
  if (!script || !props.workspaceId) { runtime.value = null; versions.value = []; return }
  loading.value = true
  try {
    const page = await api.get(`/workspaces/${props.workspaceId}/scripts/${script.id}/versions`, { params: { limit: 100, offset: 0 } })
    versions.value = page.data.items
    const version = props.config.version === 'latest' || !props.config.version ? script.latest_version : Number(props.config.version)
    runtime.value = (await api.get(`/workspaces/${props.workspaceId}/scripts/${script.id}/versions/${version}`)).data
    props.config.script_name = script.name
    props.config.inputs ||= {}
    for (const name of Object.keys(inputProperties.value)) if (props.config.inputs[name] === undefined) props.config.inputs[name] = ''
  } finally { loading.value = false }
}
function selectScript(value: string | number) {
  props.config.script_id = String(value)
  props.config.version = 'latest'
  props.config.inputs = {}
}
function selectVersion(value: string | number) { props.config.version = value; props.config.inputs = {} }
watch(() => [props.config.script_id, props.config.version, selectedScript.value?.latest_version], loadRuntime, { immediate: true })
</script>

<template>
  <div class="mt-5">
    <NodeConfigSection :title="$t('designer.nodeParameters')" :hint="$t('designer.nodeParametersHint')" kind="parameters">
      <NodeConfigSection :title="$t('designer.workspaceScript')">
        <div class="grid grid-cols-2 gap-3"><label class="field-label">{{ $t('designer.workspaceScript') }}<Select :model-value="config.script_id || ''" class="mt-1.5" :options="scripts.map(script => ({ label: `${script.name} · v${script.latest_version}`, value: script.id }))" :placeholder="$t('designer.selectScript')" @update:model-value="selectScript" /></label><label class="field-label">{{ $t('designer.scriptVersion') }}<Select :model-value="config.version || 'latest'" class="mt-1.5" :disabled="!selectedScript" :options="[{ label: $t('designer.followLatest'), value: 'latest' }, ...versions.map(version => ({ label: `v${version.version} · ${version.change_note || version.entrypoint}`, value: version.version }))]" @update:model-value="selectVersion" /></label></div>
        <p v-if="!scripts.length" class="resource-empty mt-2">{{ $t('designer.noScripts') }}</p>
      </NodeConfigSection>
      <NodeConfigSection v-if="runtime" class="mt-4 border-t border-[var(--border)] pt-4" :title="$t('scripts.outputs')" :hint="$t('scripts.outputSchemaHint')" :count="Object.keys(outputProperties).length" collapsible :default-expanded="false">
        <div class="grid gap-2 sm:grid-cols-2"><NodeSettingCard v-for="(schema, name) in outputProperties" :key="name"><div class="flex items-center gap-2"><Braces :size="13" class="text-[var(--primary)]" /><code class="min-w-0 flex-1 truncate text-xs">{{ name }}</code><span class="muted text-[9px]">{{ schema.type || 'any' }}</span></div></NodeSettingCard></div>
      </NodeConfigSection>
    </NodeConfigSection>

    <NodeConfigSection v-if="runtime" class="mt-5 border-t border-[var(--border)] pt-5" :title="$t('designer.inputVariables')" :hint="$t('scripts.inputSchemaHint')" :count="Object.keys(inputProperties).length" kind="input" collapsible>
      <div class="space-y-2"><NodeSettingCard v-for="(schema, name) in inputProperties" :key="name" :title="String(name)" :type="schema.type || 'any'" :required="requiredInputs.has(String(name))" :hint="schema.description"><VariableField v-model="config.inputs[name]" class="font-mono" :groups="variableGroups" :placeholder="$t('designer.selectUpstreamOutput')" /></NodeSettingCard><p v-if="!Object.keys(inputProperties).length" class="muted py-5 text-center text-xs">{{ $t('scripts.noInputs') }}</p></div>
    </NodeConfigSection>
    <p v-if="loading" class="muted mt-4 text-xs">{{ $t('common.loading') }}</p>
  </div>
</template>
