<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { Braces, Plus, Search } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

type PaletteTab = 'nodes' | 'tools' | 'snippets'
type PaletteSection = { key: string; items: Array<{ type: string; icon: any }> }

const props = defineProps<{ query: string; activeTab: PaletteTab; sections: PaletteSection[]; scripts: any[] }>()
const emit = defineEmits<{
  'update:query': [value: string]
  'update:activeTab': [value: PaletteTab]
  add: [type: string]
  'add-script': [script: any]
  close: []
}>()
const { t } = useI18n()
const tabs: PaletteTab[] = ['nodes', 'tools', 'snippets']
const searchInput = ref<HTMLInputElement | null>(null)
const activeIndex = ref(0)

const visibleSections = computed(() => props.sections.filter(section => props.activeTab === 'tools' ? section.key === 'tools' : section.key !== 'tools'))
const visibleScripts = computed(() => {
  const query = props.query.trim().toLocaleLowerCase()
  return props.scripts.filter(script => {
    const tags = Array.isArray(script.tags) ? script.tags.join(' ') : String(script.tags || '')
    return !query || `${script.name} ${tags}`.toLocaleLowerCase().includes(query)
  })
})
const selectableItems = computed(() => props.activeTab === 'snippets'
  ? visibleScripts.value.map(script => ({ kind: 'script' as const, key: `script:${script.id}`, script }))
  : visibleSections.value.flatMap(section => section.items.map(item => ({ kind: 'node' as const, key: `node:${item.type}`, type: item.type }))))
watch([() => props.query, () => props.activeTab, selectableItems], () => { activeIndex.value = 0 })
onMounted(() => void nextTick(() => searchInput.value?.focus()))
function itemIndex(key: string) { return selectableItems.value.findIndex(item => item.key === key) }
function chooseActive() {
  const item = selectableItems.value[activeIndex.value]
  if (!item) return
  if (item.kind === 'script') emit('add-script', item.script)
  else emit('add', item.type)
}
function onSearchKeydown(event: KeyboardEvent) {
  if (event.key === 'ArrowDown') { event.preventDefault(); activeIndex.value = Math.min(activeIndex.value + 1, selectableItems.value.length - 1) }
  else if (event.key === 'ArrowUp') { event.preventDefault(); activeIndex.value = Math.max(activeIndex.value - 1, 0) }
  else if (event.key === 'Enter') { event.preventDefault(); chooseActive() }
  else if (event.key === 'Escape') { event.preventDefault(); emit('close') }
}
</script>

<template>
  <div data-testid="node-palette" class="surface flex max-h-[560px] w-72 flex-col overflow-hidden rounded-xl shadow-2xl">
    <div class="flex h-10 shrink-0 items-end gap-1 border-b border-[var(--border)] px-2">
      <button v-for="tab in tabs" :key="tab" type="button" class="h-9 border-b-2 px-2 text-[11px] font-semibold" :class="activeTab === tab ? 'border-[var(--primary)] text-[var(--primary)]' : 'border-transparent text-[var(--muted)]'" @click="emit('update:activeTab', tab)">{{ t(`designer.paletteTabs.${tab}`) }}</button>
    </div>
    <div class="shrink-0 border-b border-[var(--border)] p-2">
      <label class="flex h-8 items-center gap-2 rounded-md bg-[var(--panel-subtle)] px-2"><Search :size="14" class="muted" /><input ref="searchInput" :value="query" class="min-w-0 flex-1 bg-transparent text-xs outline-none" :placeholder="activeTab === 'snippets' ? t('designer.searchSnippets') : t('designer.searchNodes')" @input="emit('update:query', ($event.target as HTMLInputElement).value)" @keydown="onSearchKeydown" /></label>
    </div>
    <div class="min-h-0 flex-1 overflow-y-auto p-2">
      <template v-if="activeTab !== 'snippets'">
        <div v-for="section in visibleSections" :key="section.key" class="mb-2 last:mb-0">
          <div class="muted px-2 py-1.5 text-[10px] font-semibold uppercase">{{ t(`designer.nodeCategories.${section.key}`) }}</div>
          <button v-for="item in section.items" :key="item.type" type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-2 text-left text-xs hover:bg-[var(--panel-subtle)]" :class="activeIndex === itemIndex(`node:${item.type}`) && 'bg-[var(--panel-subtle)]'" @mouseenter="activeIndex = itemIndex(`node:${item.type}`)" @click="emit('add', item.type)">
            <span class="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--primary-soft)] text-[var(--primary)]"><component :is="item.icon" :size="14" /></span>
            <span class="min-w-0 flex-1"><span class="block font-medium">{{ t(`workflow.nodes.${item.type}`) }}</span><span class="muted mt-0.5 block truncate text-[10px]">{{ t(`designer.nodeDescriptions.${item.type}`) }}</span></span><Plus class="muted" :size="13" />
          </button>
        </div>
        <div v-if="!visibleSections.length" class="muted py-8 text-center text-xs">{{ t('designer.noNodeResults') }}</div>
      </template>
      <template v-else>
        <button v-for="script in visibleScripts" :key="script.id" type="button" class="flex w-full items-center gap-2 rounded-md px-2 py-2.5 text-left hover:bg-[var(--panel-subtle)]" :class="activeIndex === itemIndex(`script:${script.id}`) && 'bg-[var(--panel-subtle)]'" @mouseenter="activeIndex = itemIndex(`script:${script.id}`)" @click="emit('add-script', script)">
          <span class="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-300"><Braces :size="15" /></span>
          <span class="min-w-0 flex-1"><span class="block truncate text-xs font-medium">{{ script.name }}</span><span class="muted mt-0.5 block text-[10px]">Python · v{{ script.latest_version }}</span></span><Plus class="muted" :size="13" />
        </button>
        <div v-if="!visibleScripts.length" class="muted py-8 text-center text-xs">{{ t('designer.noSnippets') }}</div>
      </template>
    </div>
  </div>
</template>
