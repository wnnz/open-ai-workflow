<script lang="ts">
const escapeHtml = (value: string) => value
  .replaceAll('&', '&amp;')
  .replaceAll('<', '&lt;')
  .replaceAll('>', '&gt;')
  .replaceAll('"', '&quot;')
  .replaceAll("'", '&#039;')

function renderInline(value: string) {
  const tokens: string[] = []
  let output = escapeHtml(value)
  output = output.replace(/`([^`\n]+)`/g, (_, code: string) => {
    const token = `\u0000${tokens.length}\u0000`
    tokens.push(`<code>${code}</code>`)
    return token
  })
  output = output.replace(/\[([^\]\n]+)\]\(([^)\s]+)\)/g, (_, label: string, escapedUrl: string) => {
    const rawUrl = escapedUrl.replaceAll('&amp;', '&')
    if (!/^(https?:\/\/|mailto:)/i.test(rawUrl)) return label
    const token = `\u0000${tokens.length}\u0000`
    tokens.push(`<a href="${escapedUrl}" target="_blank" rel="noopener noreferrer">${label}</a>`)
    return token
  })
  output = output
    .replace(/\*\*([^*\n]+)\*\*/g, '<strong>$1</strong>')
    .replace(/~~([^~\n]+)~~/g, '<del>$1</del>')
    .replace(/(^|[^*])\*([^*\n]+)\*/g, '$1<em>$2</em>')
  return output.replace(/\u0000(\d+)\u0000/g, (_, index: string) => tokens[Number(index)] || '')
}

export function renderSafeMarkdown(markdown: string) {
  const lines = markdown.replace(/\r\n?/g, '\n').split('\n')
  const blocks: string[] = []
  let list: string[] = []
  const flushList = () => {
    if (!list.length) return
    blocks.push(`<ul>${list.map(item => `<li>${renderInline(item)}</li>`).join('')}</ul>`)
    list = []
  }
  for (const line of lines) {
    if (line.startsWith('- ')) { list.push(line.slice(2)); continue }
    flushList()
    blocks.push(line ? `<div>${renderInline(line)}</div>` : '<br>')
  }
  flushList()
  return blocks.join('')
}
</script>

<script setup lang="ts">
import { computed } from 'vue'

const props = defineProps<{ content: string }>()
const html = computed(() => renderSafeMarkdown(props.content || ''))
</script>

<template><div class="safe-markdown break-words" v-html="html" /></template>

<style scoped>
.safe-markdown :deep(a) { color: var(--primary); text-decoration: underline; text-underline-offset: 2px; }
.safe-markdown :deep(code) { border-radius: 4px; background: color-mix(in srgb, currentColor, transparent 90%); padding: 1px 4px; font-family: ui-monospace, SFMono-Regular, Menlo, monospace; font-size: .9em; }
.safe-markdown :deep(ul) { margin: 4px 0; list-style: disc; padding-left: 18px; }
.safe-markdown :deep(li + li) { margin-top: 2px; }
</style>
