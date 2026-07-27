<script setup lang="ts">
import { computed, ref } from 'vue'
import { AlertTriangle, BookOpen, Bot, Braces, BrainCircuit, CircleHelp, CircleStop, Code2, Combine, FileText, GitBranch, Globe2, ListFilter, ListTree, MoreHorizontal, Play, RefreshCw, Repeat2, ScanText, StickyNote, Timer, UserCheck, Workflow, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import NodeActionMenu, { type NodeAction } from '@/components/designer/NodeActionMenu.vue'

const props = defineProps<{ node: any; nodeType: string; running?: boolean }>()
const emit = defineEmits<{
  run: []
  help: []
  close: []
  'update:label': [value: string]
  'update:description': [value: string]
}>()
const { t } = useI18n()
const menuOpen = ref(false)
const meta = computed(() => ({
  start: { icon: Play, tone: 'blue' }, end: { icon: CircleStop, tone: 'slate' }, llm: { icon: Bot, tone: 'violet' }, agent: { icon: BrainCircuit, tone: 'violet' },
  classifier: { icon: ListFilter, tone: 'orange' }, code: { icon: Code2, tone: 'emerald' }, script: { icon: Braces, tone: 'emerald' }, template: { icon: FileText, tone: 'sky' },
  variable: { icon: ListTree, tone: 'indigo' }, json: { icon: Code2, tone: 'cyan' }, aggregate: { icon: Combine, tone: 'indigo' }, extract: { icon: ScanText, tone: 'cyan' },
  list: { icon: ListFilter, tone: 'sky' }, knowledge: { icon: BookOpen, tone: 'amber' }, http: { icon: Globe2, tone: 'cyan' }, condition: { icon: GitBranch, tone: 'orange' },
  human: { icon: UserCheck, tone: 'amber' }, iteration: { icon: Repeat2, tone: 'blue' }, loop: { icon: RefreshCw, tone: 'violet' }, delay: { icon: Timer, tone: 'slate' },
  subworkflow: { icon: Workflow, tone: 'emerald' }, document: { icon: FileText, tone: 'rose' }, note: { icon: StickyNote, tone: 'amber' },
}[props.nodeType] || { icon: Workflow, tone: 'blue' }))

function nodeAction(action: NodeAction) {
  menuOpen.value = false
  window.dispatchEvent(new CustomEvent('workflow-node-action', { detail: { nodeId: props.node.id, action } }))
}
</script>

<template>
  <header class="shrink-0 border-b border-[var(--border)]">
    <div class="flex items-start gap-3 px-4 pb-2 pt-4">
      <span class="node-type-icon" :class="`tone-${meta.tone}`"><component :is="meta.icon" :size="17" /></span>
      <div class="min-w-0 flex-1">
        <input :value="node.data?.label" class="node-title-input" :aria-label="t('designer.editNodeTitle')" :placeholder="t('designer.addNodeTitle')" @input="emit('update:label', ($event.target as HTMLInputElement).value)" />
        <div class="mt-0.5 text-[10px] font-medium text-[var(--muted)]">{{ t(`workflow.nodes.${nodeType}`) }} · {{ node.id }}</div>
      </div>
      <button v-if="nodeType !== 'note'" type="button" class="icon-button" :title="t('designer.runStep')" :aria-label="t('designer.runStep')" :disabled="running" @click="emit('run')"><Play :size="15" /></button>
      <button type="button" class="icon-button" :title="t('designer.nodeHelp')" :aria-label="t('designer.nodeHelp')" @click="emit('help')"><CircleHelp :size="15" /></button>
      <div class="relative">
        <button type="button" class="icon-button" :title="t('designer.more')" :aria-label="t('designer.more')" @click="menuOpen = !menuOpen"><MoreHorizontal :size="16" /></button>
        <div v-if="menuOpen" class="absolute right-0 top-9 z-40" @click.stop><NodeActionMenu :show-run="nodeType !== 'note'" :protected-node="['start','end'].includes(nodeType)" :can-change="!['note','iteration','loop'].includes(nodeType)" @action="nodeAction" /></div>
      </div>
      <button type="button" class="icon-button" :title="t('designer.closeNodeSettings')" :aria-label="t('designer.closeNodeSettings')" @click="emit('close')"><X :size="16" /></button>
    </div>
    <div v-if="nodeType !== 'note'" class="px-4 pb-3">
      <input :value="node.data?.description" class="node-description-input" :aria-label="t('designer.editNodeDescription')" :placeholder="t('designer.addNodeDescription')" @input="emit('update:description', ($event.target as HTMLInputElement).value)" />
    </div>
  </header>
</template>

<style scoped>
.node-title-input { display: block; width: 100%; border: 0; background: transparent; padding: 0; color: var(--text); font-size: 14px; font-weight: 650; line-height: 20px; outline: none; }
.node-title-input:focus { color: var(--primary); }
.node-description-input { display: block; width: 100%; border: 0; border-radius: 6px; background: transparent; padding: 5px 7px; color: var(--muted); font-size: 11px; outline: none; }
.node-description-input:hover, .node-description-input:focus { background: var(--panel-subtle); color: var(--text); }
.node-type-icon { display: flex; width: 32px; height: 32px; flex: none; align-items: center; justify-content: center; border-radius: 8px; background: color-mix(in srgb, var(--node-color), transparent 88%); color: var(--node-color); }
.tone-blue { --node-color: #155eef; }.tone-slate { --node-color: #667085; }.tone-violet { --node-color: #7f56d9; }.tone-emerald { --node-color: #079455; }.tone-sky { --node-color: #026aa2; }.tone-indigo { --node-color: #444ce7; }.tone-amber { --node-color: #dc6803; }.tone-cyan { --node-color: #088ab2; }.tone-orange { --node-color: #e04f16; }.tone-rose { --node-color: #e31b54; }
</style>
