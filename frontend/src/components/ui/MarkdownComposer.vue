<script setup lang="ts">
import { nextTick, ref } from 'vue'
import { Bold, Italic, Link, List, Strikethrough } from 'lucide-vue-next'

const props = withDefaults(defineProps<{ modelValue: string; placeholder?: string; rows?: number }>(), { placeholder: '', rows: 4 })
const emit = defineEmits<{ 'update:modelValue': [value: string]; submit: [] }>()
const editor = ref<HTMLTextAreaElement | null>(null)

function replaceSelection(prefix: string, suffix = prefix, fallback = '') {
  const input = editor.value
  if (!input) return
  const start = input.selectionStart
  const end = input.selectionEnd
  const selected = props.modelValue.slice(start, end) || fallback
  const value = `${props.modelValue.slice(0, start)}${prefix}${selected}${suffix}${props.modelValue.slice(end)}`
  emit('update:modelValue', value)
  void nextTick(() => {
    input.focus()
    input.setSelectionRange(start + prefix.length, start + prefix.length + selected.length)
  })
}

function toggleList() {
  const input = editor.value
  if (!input) return
  const start = input.selectionStart
  const end = input.selectionEnd
  const lineStart = props.modelValue.lastIndexOf('\n', Math.max(0, start - 1)) + 1
  const nextBreak = props.modelValue.indexOf('\n', end)
  const lineEnd = nextBreak === -1 ? props.modelValue.length : nextBreak
  const block = props.modelValue.slice(lineStart, lineEnd)
  const valueBlock = block.split('\n').map(line => line.startsWith('- ') ? line.slice(2) : `- ${line}`).join('\n')
  emit('update:modelValue', `${props.modelValue.slice(0, lineStart)}${valueBlock}${props.modelValue.slice(lineEnd)}`)
  void nextTick(() => {
    input.focus()
    input.setSelectionRange(lineStart, lineStart + valueBlock.length)
  })
}

function insertLink() {
  const input = editor.value
  if (!input) return
  const start = input.selectionStart
  const end = input.selectionEnd
  const selected = props.modelValue.slice(start, end) || '链接文本'
  const markdown = `[${selected}](https://)`
  emit('update:modelValue', `${props.modelValue.slice(0, start)}${markdown}${props.modelValue.slice(end)}`)
  void nextTick(() => {
    input.focus()
    const urlStart = start + selected.length + 3
    input.setSelectionRange(urlStart, urlStart + 8)
  })
}

function onKeydown(event: KeyboardEvent) {
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'b') { event.preventDefault(); replaceSelection('**', '**', '加粗文本') }
  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'i') { event.preventDefault(); replaceSelection('*', '*', '斜体文本') }
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); emit('submit') }
}
</script>

<template>
  <div class="markdown-composer overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--input-bg)] focus-within:border-[var(--primary)] focus-within:ring-2 focus-within:ring-[var(--primary-soft)]">
    <div class="flex h-9 items-center gap-0.5 border-b border-[var(--border)] bg-[var(--panel-subtle)] px-2">
      <button type="button" class="format-button" :aria-label="$t('common.markdownBold')" :title="$t('common.markdownBold')" @click="replaceSelection('**', '**', $t('common.boldText'))"><Bold :size="14" /></button>
      <button type="button" class="format-button" :aria-label="$t('common.markdownItalic')" :title="$t('common.markdownItalic')" @click="replaceSelection('*', '*', $t('common.italicText'))"><Italic :size="14" /></button>
      <button type="button" class="format-button" :aria-label="$t('common.markdownStrike')" :title="$t('common.markdownStrike')" @click="replaceSelection('~~', '~~', $t('common.strikeText'))"><Strikethrough :size="14" /></button>
      <span class="mx-1 h-4 w-px bg-[var(--border)]" />
      <button type="button" class="format-button" :aria-label="$t('common.markdownLink')" :title="$t('common.markdownLink')" @click="insertLink"><Link :size="14" /></button>
      <button type="button" class="format-button" :aria-label="$t('common.markdownList')" :title="$t('common.markdownList')" @click="toggleList"><List :size="15" /></button>
    </div>
    <textarea ref="editor" class="block w-full resize-y border-0 bg-transparent px-3 py-2.5 text-xs leading-5 outline-none placeholder:text-[var(--muted)]" :rows="rows" :value="modelValue" :placeholder="placeholder" @input="emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)" @keydown="onKeydown" />
  </div>
</template>

<style scoped>
.format-button { display: inline-flex; width: 28px; height: 28px; align-items: center; justify-content: center; border-radius: 6px; color: var(--muted); }
.format-button:hover { background: var(--panel); color: var(--text); }
</style>
