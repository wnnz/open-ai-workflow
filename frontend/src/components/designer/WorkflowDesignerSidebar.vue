<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ArrowLeft,
  ChevronLeft,
  CircleHelp,
  Code2,
  Languages,
  ListTree,
  Logs,
  Monitor,
  Moon,
  Pencil,
  PanelLeftOpen,
  Search,
  Sparkles,
  Sun,
} from 'lucide-vue-next'

export type DesignerSection = 'orchestration' | 'api' | 'logs' | 'monitoring'

const props = defineProps<{
  collapsed?: boolean
  workflowName?: string
  userName?: string
  activeSection: DesignerSection
  dark?: boolean
}>()

const emit = defineEmits<{
  back: []
  toggleCollapsed: []
  search: []
  selectSection: [section: DesignerSection]
  toggleLocale: []
  toggleTheme: []
  help: []
  renameWorkflow: [name: string]
}>()

const { t } = useI18n()
const renaming = ref(false)
const draftName = ref('')
const nameInput = ref<HTMLInputElement | null>(null)

watch(() => props.workflowName, name => {
  if (!renaming.value) draftName.value = name || ''
}, { immediate: true })

async function startRename() {
  draftName.value = props.workflowName || ''
  renaming.value = true
  await nextTick()
  nameInput.value?.focus()
  nameInput.value?.select()
}

function commitRename() {
  if (!renaming.value) return
  const name = draftName.value.trim()
  renaming.value = false
  if (name && name !== props.workflowName) emit('renameWorkflow', name)
}

function cancelRename() {
  renaming.value = false
  draftName.value = props.workflowName || ''
}

const navigation: Array<{ id: DesignerSection; icon: typeof Sparkles; label: string }> = [
  { id: 'orchestration', icon: Sparkles, label: 'designer.orchestration' },
  { id: 'api', icon: Code2, label: 'designer.apiAccess' },
  { id: 'logs', icon: Logs, label: 'designer.logs' },
  { id: 'monitoring', icon: Monitor, label: 'designer.monitoring' },
]
</script>

<template>
  <aside class="designer-sidebar flex shrink-0 flex-col border-r border-[var(--border)] bg-[var(--panel)] transition-[width] duration-200" :class="collapsed ? 'w-14' : 'w-60'">
    <div class="flex h-12 items-center gap-2 border-b border-[var(--border)] px-3">
      <button v-if="!collapsed" class="icon-button" :title="t('workflow.back')" :aria-label="t('workflow.back')" @click="emit('back')"><ArrowLeft :size="16" /></button>
      <span v-if="!collapsed" class="text-sm font-medium">{{ t('studio.title') }}</span>
      <button class="icon-button" :class="!collapsed && 'ml-auto'" :title="collapsed ? t('designer.expandSidebar') : t('designer.collapseSidebar')" :aria-label="collapsed ? t('designer.expandSidebar') : t('designer.collapseSidebar')" @click="emit('toggleCollapsed')"><PanelLeftOpen v-if="collapsed" :size="16" /><ChevronLeft v-else :size="16" /></button>
    </div>

    <div v-if="!collapsed" class="border-b border-[var(--border)] p-4">
      <div class="flex items-center gap-3">
        <span class="flex h-10 w-10 items-center justify-center rounded-lg bg-violet-50 text-violet-600 dark:bg-violet-950/40"><ListTree :size="20" /></span>
        <div class="min-w-0 flex-1">
          <input v-if="renaming" ref="nameInput" v-model="draftName" class="h-7 w-full rounded-md border border-[var(--primary)] bg-[var(--panel)] px-2 text-sm font-semibold outline-none" :aria-label="t('designer.renameWorkflow')" maxlength="120" @keydown.enter.prevent="commitRename" @keydown.escape.prevent="cancelRename" @blur="commitRename" />
          <button v-else type="button" class="group flex max-w-full items-center gap-1 text-left" :title="t('designer.renameWorkflow')" @click="startRename"><span class="truncate text-sm font-semibold">{{ workflowName }}</span><Pencil class="muted shrink-0 opacity-0 transition-opacity group-hover:opacity-100 group-focus-visible:opacity-100" :size="12" /></button>
          <div class="muted mt-0.5 text-[11px]">{{ t('studio.workflow') }}</div>
        </div>
      </div>
      <button type="button" class="mt-3 flex h-8 w-full items-center gap-2 rounded-lg bg-[var(--panel-subtle)] px-2.5 text-xs text-[var(--muted)] hover:text-[var(--text)]" @click="emit('search')"><Search :size="13" /><span class="truncate">{{ t('designer.searchAnything') }}</span><kbd class="ml-auto rounded border border-[var(--border)] bg-[var(--panel)] px-1.5 py-0.5 text-[8px]">Ctrl K</kbd></button>
    </div>

    <nav class="space-y-1 p-2" :aria-label="t('studio.title')">
      <button v-for="item in navigation" :key="item.id" class="side-nav" :class="[{ active: activeSection === item.id }, collapsed && 'justify-center px-0']" :title="collapsed ? t(item.label) : undefined" :aria-current="activeSection === item.id ? 'page' : undefined" @click="emit('selectSection', item.id)"><component :is="item.icon" :size="17" /><span v-if="!collapsed">{{ t(item.label) }}</span></button>
    </nav>

    <div class="mt-auto flex items-center gap-2 border-t border-[var(--border)] p-3" :class="collapsed && 'flex-col px-2'">
      <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-[var(--primary)] text-xs font-semibold text-white" :title="userName">{{ userName?.[0]?.toUpperCase() }}</span>
      <template v-if="!collapsed">
        <span class="min-w-0 flex-1 truncate text-xs">{{ userName }}</span>
        <button class="icon-button" :title="t('designer.help')" :aria-label="t('designer.help')" @click="emit('help')"><CircleHelp :size="15" /></button>
        <button class="icon-button" :title="t('common.language')" :aria-label="t('common.language')" @click="emit('toggleLocale')"><Languages :size="15" /></button>
        <button class="icon-button" :title="dark ? t('common.light') : t('common.dark')" :aria-label="dark ? t('common.light') : t('common.dark')" @click="emit('toggleTheme')"><Sun v-if="dark" :size="15" /><Moon v-else :size="15" /></button>
      </template>
    </div>
  </aside>
</template>

<style scoped>
.designer-sidebar { letter-spacing: 0; }
.side-nav { display: flex; width: 100%; height: 36px; align-items: center; gap: 10px; border-radius: 7px; padding: 0 10px; color: var(--muted); font-size: 13px; }
.side-nav:hover { background: var(--panel-subtle); color: var(--text); }
.side-nav.active { background: var(--primary-soft); color: var(--primary); font-weight: 600; }
</style>
