<script setup lang="ts">
import { computed, nextTick, ref } from 'vue'
import { Braces, Search, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'

const props = withDefaults(defineProps<{
  modelValue: string
  groups: WorkflowVariableGroup[]
  placeholder?: string
  multiline?: boolean
  rows?: number
}>(), { placeholder: '', multiline: false, rows: 4 })
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const { t } = useI18n()
const open = ref(false)
const query = ref('')
const field = ref<HTMLInputElement | HTMLTextAreaElement | null>(null)
const selection = ref({ start: 0, end: 0 })
const filteredGroups = computed(() => {
  const term = query.value.trim().toLocaleLowerCase()
  if (!term) return props.groups
  return props.groups.map(group => ({
    ...group,
    variables: group.variables.filter(variable => `${group.label} ${variable.label} ${variable.path} ${variable.type}`.toLocaleLowerCase().includes(term)),
  })).filter(group => group.variables.length)
})

function rememberSelection() {
  selection.value = { start: field.value?.selectionStart ?? props.modelValue.length, end: field.value?.selectionEnd ?? props.modelValue.length }
}

async function insertVariable(path: string) {
  const token = `{{${path}}}`
  const { start, end } = selection.value
  const value = `${props.modelValue.slice(0, start)}${token}${props.modelValue.slice(end)}`
  emit('update:modelValue', value)
  open.value = false
  await nextTick()
  field.value?.focus()
  field.value?.setSelectionRange(start + token.length, start + token.length)
  rememberSelection()
}
</script>

<template>
  <div class="variable-field">
    <textarea
      v-if="multiline"
      ref="field"
      class="variable-control"
      :rows="rows"
      :value="modelValue"
      :placeholder="placeholder"
      @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
      @click="rememberSelection"
      @keyup="rememberSelection"
      @blur="rememberSelection"
    ></textarea>
    <input
      v-else
      ref="field"
      class="variable-control h-9"
      :value="modelValue"
      :placeholder="placeholder"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
      @click="rememberSelection"
      @keyup="rememberSelection"
      @blur="rememberSelection"
    />
    <button type="button" class="variable-trigger" :title="t('designer.selectVariable')" :aria-label="t('designer.selectVariable')" @mousedown.prevent="rememberSelection" @click="open = !open">
      <Braces :size="14" />
    </button>
    <div v-if="open" class="surface variable-popover">
      <div class="flex items-center gap-2 border-b border-[var(--border)] p-2">
        <Search :size="13" class="muted" />
        <input v-model="query" class="min-w-0 flex-1 bg-transparent text-xs outline-none" :placeholder="t('designer.searchVariables')" autofocus />
        <button type="button" class="icon-button !h-6 !w-6" :aria-label="t('common.close')" @click="open = false"><X :size="13" /></button>
      </div>
      <div class="max-h-64 overflow-y-auto p-1.5">
        <div v-for="group in filteredGroups" :key="group.nodeId" class="mb-1.5 last:mb-0">
          <div class="muted px-2 py-1 text-[10px] font-semibold">{{ group.label }}</div>
          <button v-for="variable in group.variables" :key="variable.path" type="button" class="variable-option" @click="insertVariable(variable.path)">
            <span class="min-w-0 flex-1"><span class="block truncate font-mono text-[11px] text-[var(--text)]">{{ variable.path }}</span><span class="muted mt-0.5 block truncate text-[10px]">{{ variable.label }}</span></span>
            <span class="variable-type">{{ variable.type }}</span>
          </button>
        </div>
        <div v-if="!filteredGroups.length" class="muted px-4 py-8 text-center text-xs">{{ groups.length ? t('designer.noVariableResults') : t('designer.noAvailableVariables') }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.variable-field { position: relative; }
.variable-control { width: 100%; resize: vertical; border: 1px solid var(--border); border-radius: 7px; background: var(--panel-subtle); padding: 8px 36px 8px 10px; color: var(--text); font-size: 12px; outline: none; }
.variable-control:focus { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 82%); }
.variable-trigger { position: absolute; right: 7px; top: 7px; display: flex; width: 24px; height: 24px; align-items: center; justify-content: center; border-radius: 6px; background: var(--panel); color: var(--primary); box-shadow: 0 1px 4px rgb(16 24 40 / 10%); }
.variable-trigger:hover { background: var(--primary-soft); }
.variable-popover { position: absolute; right: 0; top: calc(100% + 5px); z-index: 70; width: 300px; overflow: hidden; border-radius: 9px; box-shadow: 0 12px 30px rgb(16 24 40 / 18%); }
.variable-option { display: flex; width: 100%; align-items: center; gap: 8px; border-radius: 6px; padding: 7px 8px; text-align: left; }
.variable-option:hover { background: var(--panel-subtle); }
.variable-type { flex: none; border-radius: 4px; background: var(--panel-subtle); padding: 2px 5px; color: var(--muted); font-size: 9px; }
</style>
