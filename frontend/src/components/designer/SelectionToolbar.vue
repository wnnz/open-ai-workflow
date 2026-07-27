<script setup lang="ts">
import { Copy, Trash2, X } from 'lucide-vue-next'

defineProps<{ count: number }>()
const emit = defineEmits<{ copy: []; duplicate: []; delete: []; clear: [] }>()
</script>

<template>
  <div class="surface flex h-10 items-center gap-1 rounded-lg px-1.5 shadow-xl" role="toolbar" :aria-label="$t('designer.multiSelection')">
    <span class="flex h-7 items-center rounded-md bg-[var(--primary-soft)] px-2.5 text-[10px] font-semibold text-[var(--primary)]">{{ $t('designer.selectedCount', { count }) }}</span>
    <button type="button" class="selection-action" :title="$t('designerTools.copyNode')" :aria-label="$t('designerTools.copyNode')" @click="emit('copy')"><Copy :size="14" /><kbd>Ctrl C</kbd></button>
    <button type="button" class="selection-action" :title="$t('designerTools.duplicateNode')" :aria-label="$t('designerTools.duplicateNode')" @click="emit('duplicate')"><Copy :size="14" /><kbd>Ctrl D</kbd></button>
    <button type="button" class="selection-action text-red-600" :title="$t('designerTools.deleteSelection')" :aria-label="$t('designerTools.deleteSelection')" @click="emit('delete')"><Trash2 :size="14" /><kbd>Del</kbd></button>
    <span class="mx-0.5 h-5 w-px bg-[var(--border)]"></span>
    <button type="button" class="selection-icon" :aria-label="$t('designer.clearSelection')" @click="emit('clear')"><X :size="14" /></button>
  </div>
</template>

<style scoped>
.selection-action { display: flex; height: 28px; align-items: center; gap: 5px; border-radius: 6px; padding: 0 7px; color: var(--muted); font-size: 10px; }
.selection-action:hover { background: var(--panel-subtle); color: var(--text); }
.selection-action.text-red-600:hover { color: #d92d20; }
.selection-icon { display: flex; width: 28px; height: 28px; align-items: center; justify-content: center; border-radius: 6px; color: var(--muted); }
.selection-icon:hover { background: var(--panel-subtle); color: var(--text); }
kbd { color: inherit; font-size: 8px; font-weight: 400; opacity: .75; }
</style>
