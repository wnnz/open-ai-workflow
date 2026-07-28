<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Plus, Trash2 } from 'lucide-vue-next'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'

type JsonSchema = Record<string, any>
const props = withDefaults(defineProps<{ modelValue: JsonSchema; output?: boolean }>(), { output: false })
const emit = defineEmits<{ 'update:modelValue': [value: JsonSchema] }>()
const advanced = ref(false)
const rawSchema = ref('')
const rawError = ref('')
const properties = computed(() => props.modelValue?.properties || {})
const required = computed(() => new Set<string>(Array.isArray(props.modelValue?.required) ? props.modelValue.required : []))
const rows = computed(() => Object.entries(properties.value).map(([name, schema]) => ({ name, schema: schema as JsonSchema })))

watch(() => props.modelValue, value => {
  rawSchema.value = JSON.stringify(value || { type: 'object', properties: {} }, null, 2)
}, { immediate: true, deep: true })

function commit(propertiesValue: JsonSchema, requiredValue = required.value) {
  emit('update:modelValue', {
    ...(props.modelValue || {}),
    type: 'object',
    properties: propertiesValue,
    ...(requiredValue.size ? { required: [...requiredValue] } : { required: [] }),
  })
}
function uniqueName() {
  let index = rows.value.length + 1
  const prefix = props.output ? 'result' : 'input'
  while (properties.value[`${prefix}${index}`]) index += 1
  return `${prefix}${index}`
}
function addRow() {
  commit({ ...properties.value, [uniqueName()]: { type: 'string', description: '' } })
}
function removeRow(name: string) {
  const next = { ...properties.value }
  delete next[name]
  const requiredValue = new Set(required.value)
  requiredValue.delete(name)
  commit(next, requiredValue)
}
function renameRow(oldName: string, name: string) {
  const nextName = name.trim()
  if (!nextName || nextName === oldName || properties.value[nextName]) return
  const next: JsonSchema = {}
  for (const [key, value] of Object.entries(properties.value)) next[key === oldName ? nextName : key] = value
  const requiredValue = new Set(required.value)
  if (requiredValue.delete(oldName)) requiredValue.add(nextName)
  commit(next, requiredValue)
}
function updateRow(name: string, patch: JsonSchema) {
  commit({ ...properties.value, [name]: { ...properties.value[name], ...patch } })
}
function setRequired(name: string, checked: boolean) {
  const next = new Set(required.value)
  if (checked) next.add(name)
  else next.delete(name)
  commit(properties.value, next)
}
function defaultText(schema: JsonSchema) {
  if (schema.default === undefined) return ''
  return typeof schema.default === 'string' ? schema.default : JSON.stringify(schema.default)
}
function setDefault(name: string, schema: JsonSchema, text: string) {
  const next = { ...schema }
  if (!text.trim()) delete next.default
  else if (schema.type === 'number' || schema.type === 'integer') next.default = Number(text)
  else if (schema.type === 'boolean') next.default = text === 'true'
  else if (schema.type === 'object' || schema.type === 'array') {
    try { next.default = JSON.parse(text) } catch { return }
  } else next.default = text
  updateRow(name, next)
}
function applyRaw() {
  try {
    const parsed = JSON.parse(rawSchema.value)
    if (!parsed || parsed.type !== 'object' || typeof parsed.properties !== 'object') throw new Error('Schema must describe an object')
    rawError.value = ''
    emit('update:modelValue', parsed)
  } catch (cause: any) { rawError.value = String(cause?.message || cause) }
}
</script>

<template>
  <div>
    <div class="mb-3 flex items-center justify-between">
      <p class="muted text-xs">{{ $t(output ? 'scripts.outputSchemaHint' : 'scripts.inputSchemaHint') }}</p>
      <div class="flex items-center gap-2"><button type="button" class="text-xs text-[var(--primary)] hover:underline" @click="advanced = !advanced">{{ advanced ? $t('scripts.parameterEditor') : $t('scripts.advancedSchema') }}</button><IconButton v-if="!advanced" :label="$t('scripts.addParameter')" size="sm" @click="addRow"><Plus :size="14" /></IconButton></div>
    </div>
    <div v-if="advanced">
      <Textarea v-model="rawSchema" class="h-80 font-mono !text-xs" spellcheck="false" @blur="applyRaw" />
      <p v-if="rawError" class="mt-2 text-xs text-red-600">{{ rawError }}</p>
    </div>
    <div v-else class="space-y-2">
      <div v-for="row in rows" :key="row.name" class="grid grid-cols-[120px_110px_70px_minmax(110px,.8fr)_minmax(140px,1fr)_30px] items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-2">
        <InputText :model-value="row.name" class="font-mono !text-xs" @change="renameRow(row.name, ($event.target as HTMLInputElement).value)" />
        <Select :model-value="row.schema.type || 'string'" :options="['string','number','integer','boolean','object','array'].map(value => ({ label: value, value }))" @update:model-value="updateRow(row.name, { type: $event })" />
        <label class="flex items-center gap-1.5 text-xs"><input type="checkbox" :checked="required.has(row.name)" @change="setRequired(row.name, ($event.target as HTMLInputElement).checked)">{{ $t('scripts.required') }}</label>
        <InputText :model-value="defaultText(row.schema)" :placeholder="$t('scripts.defaultValue')" @change="setDefault(row.name, row.schema, ($event.target as HTMLInputElement).value)" />
        <InputText :model-value="row.schema.description || ''" :placeholder="$t('common.description')" @input="updateRow(row.name, { description: ($event.target as HTMLInputElement).value })" />
        <IconButton :label="$t('scripts.removeParameter')" tone="danger" size="sm" @click="removeRow(row.name)"><Trash2 :size="13" /></IconButton>
      </div>
      <button v-if="!rows.length" type="button" class="flex w-full items-center justify-center gap-2 rounded-lg border border-dashed border-[var(--border)] py-8 text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="addRow"><Plus :size="14" />{{ $t('scripts.addParameter') }}</button>
    </div>
  </div>
</template>
