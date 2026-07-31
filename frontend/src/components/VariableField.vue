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
  controlClass?: string
  spellcheck?: boolean
}>(), { placeholder: '', multiline: false, rows: 4, controlClass: '', spellcheck: true })
const emit = defineEmits<{ 'update:modelValue': [value: string]; focus: [event: FocusEvent]; blur: [event: FocusEvent] }>()
const { t } = useI18n()
const open = ref(false)
const query = ref('')
const container = ref<HTMLDivElement | null>(null)
const field = ref<HTMLInputElement | HTMLTextAreaElement | null>(null)
const selection = ref({ start: 0, end: 0 })
const tokenRange = ref<{ start: number; end: number } | null>(null)
const openedByTyping = ref(false)
const popoverStyle = ref<Record<string, string>>({ right: '0', top: 'calc(100% + 5px)' })
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

function handleBlur(event: FocusEvent) {
  rememberSelection()
  emit('blur', event)
}

const mirrorProperties = [
  'border-bottom-width', 'border-left-width', 'border-right-width', 'border-top-width',
  'box-sizing', 'font-family', 'font-size', 'font-style', 'font-weight', 'letter-spacing',
  'line-height', 'padding-bottom', 'padding-left', 'padding-right', 'padding-top',
  'tab-size', 'text-align', 'text-indent', 'text-transform', 'word-spacing',
]

function caretViewportPosition(control: HTMLInputElement | HTMLTextAreaElement, offset: number) {
  const computed = window.getComputedStyle(control)
  const rect = control.getBoundingClientRect()
  const mirror = document.createElement('div')
  mirror.style.position = 'fixed'
  mirror.style.left = `${rect.left}px`
  mirror.style.top = `${rect.top}px`
  mirror.style.width = `${rect.width}px`
  mirror.style.height = 'auto'
  mirror.style.visibility = 'hidden'
  mirror.style.pointerEvents = 'none'
  mirror.style.overflow = 'visible'
  mirror.style.whiteSpace = control instanceof HTMLTextAreaElement ? 'pre-wrap' : 'pre'
  mirror.style.overflowWrap = control instanceof HTMLTextAreaElement ? 'break-word' : 'normal'
  mirror.style.wordBreak = computed.wordBreak
  for (const property of mirrorProperties) mirror.style.setProperty(property, computed.getPropertyValue(property))
  mirror.textContent = control.value.slice(0, offset)
  const marker = document.createElement('span')
  marker.textContent = '\u200b'
  mirror.append(marker)
  document.body.append(mirror)
  const markerRect = marker.getBoundingClientRect()
  const lineHeight = Number.parseFloat(computed.lineHeight) || Number.parseFloat(computed.fontSize) * 1.2 || 16
  const position = {
    left: markerRect.left - control.scrollLeft,
    top: markerRect.top - control.scrollTop + lineHeight,
  }
  mirror.remove()
  return position
}

function positionPopoverAtToken(offset: number) {
  const control = field.value
  const root = container.value
  if (!control || !root) return
  const caret = caretViewportPosition(control, offset)
  const rootRect = root.getBoundingClientRect()
  const popoverWidth = Math.min(300, window.innerWidth - 16)
  const desiredLeft = caret.left - rootRect.left
  const minLeft = 8 - rootRect.left
  const maxLeft = Math.max(minLeft, window.innerWidth - rootRect.left - popoverWidth - 8)
  popoverStyle.value = {
    left: `${Math.max(minLeft, Math.min(desiredLeft, maxLeft))}px`,
    right: 'auto',
    top: `${Math.max(0, caret.top - rootRect.top + 5)}px`,
  }
}

function resetPopoverPosition() {
  popoverStyle.value = { left: 'auto', right: '0', top: 'calc(100% + 5px)' }
}

function handleInput(event: Event) {
  const target = event.target as HTMLInputElement | HTMLTextAreaElement
  const value = target.value
  const cursor = target.selectionStart ?? value.length
  emit('update:modelValue', value)
  selection.value = { start: cursor, end: target.selectionEnd ?? cursor }

  const beforeCursor = value.slice(0, cursor)
  const opening = beforeCursor.lastIndexOf('{{')
  const hasClosingToken = opening >= 0 && beforeCursor.slice(opening + 2).includes('}}')
  if (opening >= 0 && !hasClosingToken) {
    tokenRange.value = { start: opening, end: cursor }
    query.value = beforeCursor.slice(opening + 2).trim()
    openedByTyping.value = true
    open.value = true
    positionPopoverAtToken(opening)
  } else {
    tokenRange.value = null
    if (openedByTyping.value) open.value = false
    openedByTyping.value = false
  }
}

function togglePicker() {
  if (open.value && !openedByTyping.value) {
    open.value = false
    return
  }
  tokenRange.value = null
  openedByTyping.value = false
  query.value = ''
  resetPopoverPosition()
  open.value = true
}

function handleControlScroll() {
  if (openedByTyping.value && tokenRange.value) positionPopoverAtToken(tokenRange.value.start)
}

function closePicker() {
  open.value = false
  openedByTyping.value = false
  tokenRange.value = null
}

async function insertVariable(path: string) {
  const token = `{{${path}}}`
  const { start, end } = tokenRange.value || selection.value
  const currentValue = field.value?.value ?? props.modelValue
  const value = `${currentValue.slice(0, start)}${token}${currentValue.slice(end)}`
  emit('update:modelValue', value)
  closePicker()
  await nextTick()
  field.value?.focus()
  field.value?.setSelectionRange(start + token.length, start + token.length)
  rememberSelection()
}

async function insertText(text: string) {
  const { start, end } = selection.value
  const currentValue = field.value?.value ?? props.modelValue
  emit('update:modelValue', `${currentValue.slice(0, start)}${text}${currentValue.slice(end)}`)
  await nextTick()
  field.value?.focus()
  field.value?.setSelectionRange(start + text.length, start + text.length)
  rememberSelection()
}

defineExpose({
  focus: () => field.value?.focus(),
  blur: () => field.value?.blur(),
  insertText,
})
</script>

<template>
  <div ref="container" class="variable-field">
    <textarea
      v-if="multiline"
      ref="field"
      class="variable-control bg-[var(--input-bg)]"
      :class="controlClass"
      :rows="rows"
      :value="modelValue"
      :placeholder="placeholder"
      :spellcheck="spellcheck"
      @input="handleInput"
      @click="rememberSelection"
      @keyup="rememberSelection"
      @focus="emit('focus', $event)"
      @blur="handleBlur"
      @scroll="handleControlScroll"
      @keydown.esc="closePicker"
    ></textarea>
    <input
      v-else
      ref="field"
      class="variable-control h-9 bg-[var(--input-bg)]"
      :class="controlClass"
      :value="modelValue"
      :placeholder="placeholder"
      :spellcheck="spellcheck"
      @input="handleInput"
      @click="rememberSelection"
      @keyup="rememberSelection"
      @focus="emit('focus', $event)"
      @blur="handleBlur"
      @scroll="handleControlScroll"
      @keydown.esc="closePicker"
    />
    <button type="button" class="variable-trigger" :title="t('designer.selectVariable')" :aria-label="t('designer.selectVariable')" @mousedown.prevent="rememberSelection" @click="togglePicker">
      <Braces :size="14" />
    </button>
    <div v-if="open" class="surface variable-popover" :style="popoverStyle">
      <div class="flex items-center gap-2 border-b border-[var(--border)] p-2">
        <Search :size="13" class="muted" />
        <input v-model="query" class="min-w-0 flex-1 bg-transparent text-xs outline-none" :placeholder="t('designer.searchVariables')" />
        <button type="button" class="icon-button !h-6 !w-6" :aria-label="t('common.close')" @click="closePicker"><X :size="13" /></button>
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
.variable-control { width: 100%; resize: vertical; border: 1px solid var(--border); border-radius: 7px; padding: 8px 36px 8px 10px; color: var(--text); font-size: 12px; outline: none; }
.variable-control:focus { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 82%); }
.variable-trigger { position: absolute; right: 7px; top: 7px; display: flex; width: 24px; height: 24px; align-items: center; justify-content: center; border-radius: 6px; background: var(--panel); color: var(--primary); box-shadow: 0 1px 4px rgb(16 24 40 / 10%); }
.variable-trigger:hover { background: var(--primary-soft); }
.variable-popover { position: absolute; z-index: 70; width: min(300px, calc(100vw - 16px)); overflow: hidden; border-radius: 9px; box-shadow: 0 12px 30px rgb(16 24 40 / 18%); }
.variable-option { display: flex; width: 100%; align-items: center; gap: 8px; border-radius: 6px; padding: 7px 8px; text-align: left; }
.variable-option:hover { background: var(--panel-subtle); }
.variable-type { flex: none; border-radius: 4px; background: var(--panel-subtle); padding: 2px 5px; color: var(--muted); font-size: 9px; }
</style>
