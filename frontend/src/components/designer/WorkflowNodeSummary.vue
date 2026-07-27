<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  nodeType: string
  config?: Record<string, any>
  fallback?: string
}>()

const { t } = useI18n()

type SummaryRow = {
  key: string
  label: string
  meta?: string
  required?: boolean
}

const startRows = computed<SummaryRow[]>(() => {
  const fields = Array.isArray(props.config?.input_fields) ? props.config.input_fields : []
  return fields.slice(0, 3).map((field: any, index: number) => ({
    key: String(field.name || index),
    label: String(field.name || field.label || t('designer.unnamedField')),
    meta: t(`designer.fieldTypes.${field.type || 'text'}`),
    required: Boolean(field.required),
  }))
})

const endRows = computed<SummaryRow[]>(() => {
  const outputs = Array.isArray(props.config?.outputs) ? props.config.outputs : []
  return outputs.slice(0, 3).map((output: any, index: number) => ({
    key: String(output.name || index),
    label: String(output.name || `output_${index + 1}`),
    meta: String(output.type || 'Any'),
  }))
})

const rows = computed(() => props.nodeType === 'start' ? startRows.value : props.nodeType === 'end' ? endRows.value : [])
const totalRows = computed(() => props.nodeType === 'start'
  ? (Array.isArray(props.config?.input_fields) ? props.config.input_fields.length : 0)
  : (Array.isArray(props.config?.outputs) ? props.config.outputs.length : 0))

const compactDetail = computed(() => {
  if (props.nodeType === 'llm' || props.nodeType === 'agent') return String(props.config?.model || props.fallback || 'LLM')
  if (props.nodeType === 'http') return [String(props.config?.method || 'GET').toUpperCase(), String(props.config?.url || '')].filter(Boolean).join('  ')
  if (props.nodeType === 'script') return [String(props.config?.script_name || props.fallback || 'Python'), props.config?.version ? `v${props.config.version}` : ''].filter(Boolean).join('  ·  ')
  if (props.nodeType === 'document') return t(`designer.documentOperations.${props.config?.operation || 'extract'}`)
  return props.fallback || ''
})
</script>

<template>
  <div v-if="rows.length" class="node-summary-list">
    <div v-for="row in rows" :key="row.key" class="node-summary-row">
      <span class="node-summary-dot"></span>
      <span class="min-w-0 flex-1 truncate font-mono">{{ row.label }}</span>
      <span v-if="row.required" class="node-summary-required">{{ t('designer.required') }}</span>
      <span v-else-if="row.meta" class="node-summary-meta">{{ row.meta }}</span>
    </div>
    <div v-if="totalRows > rows.length" class="node-summary-more">+{{ totalRows - rows.length }}</div>
  </div>
  <div v-else class="node-summary-compact">
    <span class="node-summary-dot"></span>
    <span class="truncate">{{ compactDetail }}</span>
  </div>
</template>

<style scoped>
.node-summary-list { margin-top: 9px; display: grid; gap: 4px; }
.node-summary-row { display: flex; height: 25px; align-items: center; gap: 6px; overflow: hidden; border-radius: 5px; background: var(--panel-subtle); padding: 0 8px; color: var(--text); font-size: 10px; }
.node-summary-dot { width: 6px; height: 6px; flex: none; border-radius: 999px; background: var(--node-color); opacity: .72; }
.node-summary-meta { max-width: 76px; flex: none; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--muted); }
.node-summary-required { flex: none; color: #d92d20; }
.node-summary-more { padding-right: 3px; text-align: right; color: var(--muted); font-size: 9px; }
.node-summary-compact { margin-top: 9px; display: flex; height: 25px; align-items: center; gap: 6px; overflow: hidden; border-radius: 5px; background: var(--panel-subtle); padding: 0 8px; color: var(--node-color); font-size: 10px; font-weight: 500; }
</style>
