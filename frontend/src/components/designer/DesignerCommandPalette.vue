<script setup lang="ts">
import { computed, nextTick, ref, watch } from 'vue'
import { Command, CornerDownLeft, LocateFixed, Plus, Search, X } from 'lucide-vue-next'

type AddItem = { type: string; label: string; description?: string }
type ActionItem = { id: string; label: string; shortcut?: string }
type ResultItem = { key: string; kind: 'action' | 'node' | 'add'; id: string; label: string; description?: string; shortcut?: string }

const props = defineProps<{ open: boolean; nodes: any[]; addItems: AddItem[]; actions: ActionItem[] }>()
const emit = defineEmits<{ close: []; focus: [nodeId: string]; add: [type: string]; action: [id: string] }>()
const query = ref(''); const activeIndex = ref(0); const searchInput = ref<HTMLInputElement | null>(null)

const results = computed<ResultItem[]>(() => {
  const raw = query.value.trim(); const commandOnly = raw.startsWith('/'); const category = raw.startsWith('@') ? raw.slice(1).toLocaleLowerCase() : ''; const term = (commandOnly ? raw.slice(1) : raw.startsWith('@') ? '' : raw).toLocaleLowerCase()
  const matches = (value: string) => !term || value.toLocaleLowerCase().includes(term)
  const actions = props.actions.filter(item => matches(item.label)).map(item => ({ key: `action:${item.id}`, kind: 'action' as const, ...item }))
  if (commandOnly) return actions
  const nodes = props.nodes.filter(node => matches(`${node.data?.label || ''} ${node.data?.description || ''} ${node.data?.nodeType || node.type || ''}`)).map(node => ({ key: `node:${node.id}`, kind: 'node' as const, id: node.id, label: String(node.data?.label || node.id), description: String(node.data?.description || '') }))
  const add = props.addItems.filter(item => matches(`${item.label} ${item.description || ''}`)).map(item => ({ key: `add:${item.type}`, kind: 'add' as const, id: item.type, label: item.label, description: item.description }))
  if (category === 'node' || category === 'nodes' || category === '节点') return nodes
  if (category === 'add' || category === '添加') return add
  if (category === 'command' || category === 'commands' || category === '命令') return actions
  return [...actions, ...nodes, ...add]
})

watch(() => props.open, async open => { if (!open) return; query.value = ''; activeIndex.value = 0; await nextTick(); searchInput.value?.focus() })
watch(results, () => { activeIndex.value = Math.min(activeIndex.value, Math.max(0, results.value.length - 1)) })

function choose(item: ResultItem) {
  if (item.kind === 'action') emit('action', item.id)
  else if (item.kind === 'node') emit('focus', item.id)
  else emit('add', item.id)
  emit('close')
}
function onKeydown(event: KeyboardEvent) {
  if (event.key === 'Escape') { event.preventDefault(); emit('close'); return }
  if (event.key === 'ArrowDown') { event.preventDefault(); activeIndex.value = (activeIndex.value + 1) % Math.max(1, results.value.length) }
  else if (event.key === 'ArrowUp') { event.preventDefault(); activeIndex.value = (activeIndex.value - 1 + Math.max(1, results.value.length)) % Math.max(1, results.value.length) }
  else if (event.key === 'Enter' && results.value[activeIndex.value]) { event.preventDefault(); choose(results.value[activeIndex.value]) }
}
function kindLabel(kind: ResultItem['kind']) { return kind === 'action' ? 'designer.commandKinds.action' : kind === 'node' ? 'designer.commandKinds.node' : 'designer.commandKinds.add' }
</script>

<template>
  <Teleport to="body">
    <div v-if="open" class="fixed inset-0 z-[100] flex justify-center bg-slate-950/35 px-5 pt-[12vh]" role="presentation" @mousedown.self="emit('close')">
      <section class="surface flex max-h-[620px] w-full max-w-2xl flex-col overflow-hidden rounded-xl shadow-2xl" role="dialog" aria-modal="true" :aria-label="$t('designer.searchAnything')">
        <header class="flex h-14 items-center gap-3 border-b border-[var(--border)] px-4"><Search :size="18" class="text-[var(--muted)]" /><input ref="searchInput" v-model="query" class="min-w-0 flex-1 bg-transparent text-sm outline-none" role="combobox" :aria-label="$t('designer.searchAnything')" :placeholder="$t('designer.searchAnything')" aria-autocomplete="list" @keydown="onKeydown" /><kbd>Ctrl K</kbd><button type="button" class="icon-button" :aria-label="$t('common.close')" @click="emit('close')"><X :size="15" /></button></header>
        <div v-if="!query" class="flex flex-wrap gap-2 border-b border-[var(--border)] px-4 py-2 text-[10px] text-[var(--muted)]"><span>{{ $t('designer.commandHintSearch') }}</span><span>·</span><span>{{ $t('designer.commandHintCategory') }}</span><span>·</span><span>{{ $t('designer.commandHintCommands') }}</span></div>
        <div class="min-h-0 flex-1 overflow-y-auto p-2" role="listbox">
          <button v-for="(item, index) in results" :key="item.key" type="button" class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left" :class="index === activeIndex ? 'bg-[var(--primary-soft)]' : 'hover:bg-[var(--panel-subtle)]'" role="option" :aria-selected="index === activeIndex" @mouseenter="activeIndex = index" @click="choose(item)">
            <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg" :class="index === activeIndex ? 'bg-[var(--panel)] text-[var(--primary)]' : 'bg-[var(--panel-subtle)] text-[var(--muted)]'"><Command v-if="item.kind === 'action'" :size="15" /><LocateFixed v-else-if="item.kind === 'node'" :size="15" /><Plus v-else :size="15" /></span>
            <span class="min-w-0 flex-1"><span class="block truncate text-xs font-semibold">{{ item.label }}</span><span v-if="item.description" class="muted mt-0.5 block truncate text-[10px]">{{ item.description }}</span></span>
            <span class="rounded bg-[var(--panel-subtle)] px-1.5 py-1 text-[8px] font-medium uppercase text-[var(--muted)]">{{ $t(kindLabel(item.kind)) }}</span><kbd v-if="item.shortcut">{{ item.shortcut }}</kbd><CornerDownLeft v-else-if="index === activeIndex" :size="12" class="muted" />
          </button>
          <div v-if="!results.length" class="muted py-16 text-center text-xs">{{ $t('designer.noCommandResults') }}</div>
        </div>
        <footer class="flex h-9 items-center gap-4 border-t border-[var(--border)] px-4 text-[9px] text-[var(--muted)]"><span>↑↓ {{ $t('designer.commandNavigate') }}</span><span>↵ {{ $t('designer.commandChoose') }}</span><span>Esc {{ $t('common.close') }}</span></footer>
      </section>
    </div>
  </Teleport>
</template>

<style scoped>kbd { border: 1px solid var(--border); border-radius: 5px; background: var(--panel-subtle); padding: 2px 5px; color: var(--muted); font-size: 9px; font-weight: 400; }</style>
