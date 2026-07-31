<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import NodeInspectorHeader from './NodeInspectorHeader.vue'
import NodeRunResultPanel from './NodeRunResultPanel.vue'

export type InspectorTab = 'settings' | 'run'

defineProps<{
  node: any
  nodeType: string
  tab: InspectorTab
  running?: boolean
  result?: any
  nameError?: string
}>()

const emit = defineEmits<{
  'update:tab': [tab: InspectorTab]
  'update:label': [label: string]
  'update:description': [description: string]
  run: []
  help: []
  close: []
}>()

const { t } = useI18n()
</script>

<template>
  <aside class="inspector relative z-30 flex w-[420px] max-w-[42vw] shrink-0 flex-col border-l border-[var(--border)] bg-[var(--panel)]">
    <NodeInspectorHeader
      :node="node"
      :node-type="nodeType"
      :running="running"
      :name-error="nameError"
      @update:label="emit('update:label', $event)"
      @update:description="emit('update:description', $event)"
      @run="emit('run')"
      @help="emit('help')"
      @close="emit('close')"
    />
    <div v-if="nodeType !== 'note'" class="flex border-b border-[var(--border)] px-4" role="tablist">
      <button class="inspector-tab" role="tab" :aria-selected="tab === 'settings'" :class="{ active: tab === 'settings' }" @click="emit('update:tab', 'settings')">{{ t('designer.settings') }}</button>
      <button class="inspector-tab" role="tab" :aria-selected="tab === 'run'" :class="{ active: tab === 'run' }" @click="emit('update:tab', 'run')">{{ t('designer.lastRun') }}</button>
    </div>
    <div v-if="tab === 'settings'" class="inspector-settings min-h-0 flex-1 overflow-y-auto px-4 pb-8"><slot name="settings" /></div>
    <div v-else class="min-h-0 flex-1 overflow-y-auto p-4"><NodeRunResultPanel :result="result" /></div>
  </aside>
</template>

<style scoped>
.inspector { --control-height: 2.25rem; --control-font-size: 0.75rem; --control-radius: 0.4375rem; }
.inspector-tab { height: 40px; border-bottom: 2px solid transparent; padding: 0 12px; color: var(--muted); font-size: 12px; }
.inspector-tab.active { border-color: var(--primary); color: var(--primary); font-weight: 600; }
</style>
