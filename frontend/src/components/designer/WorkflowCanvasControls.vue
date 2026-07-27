<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  Clipboard,
  Copy,
  Hand,
  History,
  LayoutDashboard,
  Maximize2,
  MessageSquare,
  MoreHorizontal,
  MousePointer2,
  Plus,
  Redo2,
  StickyNote,
  Trash2,
  Undo2,
  ZoomIn,
  ZoomOut,
} from 'lucide-vue-next'

defineProps<{
  interactionMode: 'pointer' | 'hand'
  annotationActive?: boolean
  commentsActive?: boolean
  canCopy?: boolean
  canPaste?: boolean
  canDelete?: boolean
  canUndo?: boolean
  canRedo?: boolean
  zoomPercent: number
}>()

const emit = defineEmits<{
  addNode: []
  toggleAnnotation: []
  fitView: []
  'update:interactionMode': [mode: 'pointer' | 'hand']
  toggleComments: []
  autoLayout: []
  copy: []
  paste: []
  delete: []
  undo: []
  redo: []
  history: []
  zoomOut: []
  zoomIn: []
}>()

const { t } = useI18n()
const actionsOpen = ref(false)

function runAction(action: 'copy' | 'paste' | 'delete') {
  actionsOpen.value = false
  if (action === 'copy') emit('copy')
  else if (action === 'paste') emit('paste')
  else emit('delete')
}
</script>

<template>
  <div class="surface absolute left-4 top-1/2 z-10 flex -translate-y-1/2 flex-col overflow-visible rounded-lg shadow-lg">
    <button data-testid="open-node-palette" class="canvas-mode-button" :title="t('workflow.addNode')" @click="actionsOpen = false; emit('addNode')"><Plus :size="16" /></button>
    <button class="canvas-mode-button" :class="{ active: annotationActive }" :title="t('designer.addNote')" @click="actionsOpen = false; emit('toggleAnnotation')"><StickyNote :size="15" /></button>
    <button class="canvas-mode-button" :title="t('designer.fitView')" @click="actionsOpen = false; emit('fitView')"><Maximize2 :size="15" /></button>
    <span class="mx-2 h-px bg-[var(--border)]"></span>
    <button class="canvas-mode-button" :class="{ active: interactionMode === 'pointer' }" :title="t('designerTools.pointer')" @click="actionsOpen = false; emit('update:interactionMode', 'pointer')"><MousePointer2 :size="15" /></button>
    <button class="canvas-mode-button" :class="{ active: interactionMode === 'hand' }" :title="t('designerTools.hand')" @click="actionsOpen = false; emit('update:interactionMode', 'hand')"><Hand :size="15" /></button>
    <button class="canvas-mode-button" :class="{ active: commentsActive }" :title="t('designer.comments')" @click="actionsOpen = false; emit('toggleComments')"><MessageSquare :size="15" /></button>
    <button class="canvas-mode-button" :title="t('designerTools.autoLayout')" @click="actionsOpen = false; emit('autoLayout')"><LayoutDashboard :size="15" /></button>
    <button class="canvas-mode-button" :class="{ active: actionsOpen }" :title="t('designerTools.more')" @click="actionsOpen = !actionsOpen"><MoreHorizontal :size="16" /></button>
    <div v-if="actionsOpen" class="surface absolute left-11 bottom-0 w-40 rounded-lg p-1.5 shadow-xl">
      <button class="canvas-action-row" :disabled="!canCopy" @click="runAction('copy')"><Copy :size="14" />{{ t('designerTools.copyNode') }}</button>
      <button class="canvas-action-row" :disabled="!canPaste" @click="runAction('paste')"><Clipboard :size="14" />{{ t('designerTools.pasteNode') }}</button>
      <button class="canvas-action-row text-red-600" :disabled="!canDelete" @click="runAction('delete')"><Trash2 :size="14" />{{ t('designerTools.deleteSelection') }}</button>
    </div>
  </div>

  <div class="surface absolute bottom-4 left-4 z-10 flex h-9 items-center overflow-hidden rounded-lg shadow-lg">
    <button class="canvas-history-button" :disabled="!canUndo" :title="t('designerTools.undo')" @click="emit('undo')"><Undo2 :size="15" /></button>
    <button class="canvas-history-button" :disabled="!canRedo" :title="t('designerTools.redo')" @click="emit('redo')"><Redo2 :size="15" /></button>
    <span class="h-5 w-px bg-[var(--border)]"></span>
    <button class="canvas-history-button" :title="t('designer.changeHistory')" @click="emit('history')"><History :size="15" /></button>
  </div>

  <div class="surface absolute bottom-4 right-4 z-10 flex h-9 items-center overflow-hidden rounded-lg shadow-lg">
    <button class="canvas-history-button" :title="t('designerTools.zoomOut')" @click="emit('zoomOut')"><ZoomOut :size="15" /></button>
    <span class="w-12 text-center text-xs text-[var(--muted)]">{{ zoomPercent }}%</span>
    <button class="canvas-history-button" :title="t('designerTools.zoomIn')" @click="emit('zoomIn')"><ZoomIn :size="15" /></button>
  </div>
</template>
