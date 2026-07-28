<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Braces } from 'lucide-vue-next'
import api from '@/api/client'
import VariableField from '@/components/VariableField.vue'
import Select from '@/volt/Select.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import NodeConfigSection from './NodeConfigSection.vue'

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
  <div class="mt-5 space-y-5">
    <NodeConfigSection :title="$t('designer.workspaceScript')">
      <div class="grid grid-cols-2 gap-3"><label class="field-label">{{ $t('designer.workspaceScript') }}<Select :model-value="config.script_id || ''" class="mt-1.5" :options="scripts.map(script => ({ label: `${script.name} · v${script.latest_version}`, value: script.id }))" :placeholder="$t('designer.selectScript')" @update:model-value="selectScript" /></label><label class="field-label">{{ $t('designer.scriptVersion') }}<Select :model-value="config.version || 'latest'" class="mt-1.5" :disabled="!selectedScript" :options="[{ label: $t('designer.followLatest'), value: 'latest' }, ...versions.map(version => ({ label: `v${version.version} · ${version.change_note || version.entrypoint}`, value: version.version }))]" @update:model-value="selectVersion" /></label></div>
      <p v-if="!scripts.length" class="resource-empty">{{ $t('designer.noScripts') }}</p>
    </NodeConfigSection>
    <NodeConfigSection v-if="runtime" :title="$t('scripts.inputs')" :hint="$t('scripts.inputSchemaHint')" :count="Object.keys(inputProperties).length">
      <div class="space-y-2"><label v-for="(schema, name) in inputProperties" :key="name" class="block rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-2.5"><span class="flex items-center gap-2 text-xs font-semibold"><code>{{ name }}</code><span class="rounded bg-[var(--panel)] px-1.5 py-0.5 text-[9px] text-[var(--muted)]">{{ schema.type || 'any' }}</span><span v-if="requiredInputs.has(String(name))" class="text-red-500">*</span></span><span v-if="schema.description" class="muted mt-1 block text-[10px]">{{ schema.description }}</span><VariableField v-model="config.inputs[name]" class="mt-2 font-mono" :groups="variableGroups" :placeholder="$t('designer.selectUpstreamOutput')" /></label><p v-if="!Object.keys(inputProperties).length" class="muted py-5 text-center text-xs">{{ $t('scripts.noInputs') }}</p></div>
    </NodeConfigSection>
    <NodeConfigSection v-if="runtime" :title="$t('scripts.outputs')" :hint="$t('scripts.outputSchemaHint')" :count="Object.keys(outputProperties).length">
      <div class="grid gap-2 sm:grid-cols-2"><div v-for="(schema, name) in outputProperties" :key="name" class="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] px-3 py-2"><Braces :size="13" class="text-[var(--primary)]" /><code class="min-w-0 flex-1 truncate text-xs">{{ name }}</code><span class="muted text-[9px]">{{ schema.type || 'any' }}</span></div></div>
    </NodeConfigSection>
    <p v-if="loading" class="muted text-xs">{{ $t('common.loading') }}</p>
  </div>
</template>
