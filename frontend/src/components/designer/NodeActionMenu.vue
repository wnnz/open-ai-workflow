<script setup lang="ts">
import { Copy, Play, RefreshCw, Trash2 } from 'lucide-vue-next'

export type NodeAction = 'run' | 'change' | 'copy' | 'duplicate' | 'delete'

withDefaults(defineProps<{ protectedNode?: boolean; showRun?: boolean; canChange?: boolean }>(), { protectedNode: false, showRun: true, canChange: true })
const emit = defineEmits<{ action: [action: NodeAction] }>()
</script>

<template>
  <div class="surface w-44 rounded-lg p-1.5 shadow-xl" role="menu">
    <button v-if="showRun" type="button" class="node-action-row" role="menuitem" @click="emit('action', 'run')"><Play :size="14" />{{ $t('designer.runThisNode') }}<kbd>Alt R</kbd></button>
    <button type="button" class="node-action-row" :disabled="!canChange" role="menuitem" @click="emit('action', 'change')"><RefreshCw :size="14" />{{ $t('designer.changeNode') }}</button>
    <span class="mx-1 my-1 block h-px bg-[var(--border)]"></span>
    <button type="button" class="node-action-row" :disabled="protectedNode" role="menuitem" @click="emit('action', 'copy')"><Copy :size="14" />{{ $t('designerTools.copyNode') }}<kbd>Ctrl C</kbd></button>
    <button type="button" class="node-action-row" :disabled="protectedNode" role="menuitem" @click="emit('action', 'duplicate')"><Copy :size="14" />{{ $t('designerTools.duplicateNode') }}<kbd>Ctrl D</kbd></button>
    <span class="mx-1 my-1 block h-px bg-[var(--border)]"></span>
    <button type="button" class="node-action-row text-red-600" :disabled="protectedNode" role="menuitem" @click="emit('action', 'delete')"><Trash2 :size="14" />{{ $t('common.delete') }}<kbd>Del</kbd></button>
  </div>
</template>

<style scoped>
.node-action-row { display: flex; width: 100%; height: 32px; align-items: center; gap: 8px; border-radius: 6px; padding: 0 8px; font-size: 11px; text-align: left; }
.node-action-row:hover:not(:disabled) { background: var(--panel-subtle); }
.node-action-row:disabled { cursor: not-allowed; opacity: .35; }
kbd { margin-left: auto; color: var(--muted); font-size: 9px; font-weight: 400; }
</style>
