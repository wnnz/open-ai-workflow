<script setup lang="ts">
import { computed } from 'vue'
import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@vue-flow/core'
import { Plus, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'

const props = defineProps<EdgeProps>()
const { t } = useI18n()
const connectedToSelection = computed(() => Boolean(props.sourceNode?.selected || props.targetNode?.selected))
const branchLabel = computed(() => {
  if (props.sourceHandleId === 'true') return 'IF'
  if (props.sourceHandleId === 'false') return 'ELSE'
  if (String(props.sourceHandleId || '').startsWith('category:')) return String(props.data?.branchLabel || '')
  return ''
})
const path = computed(() => getBezierPath({
  sourceX: props.sourceX,
  sourceY: props.sourceY,
  sourcePosition: props.sourcePosition,
  targetX: props.targetX,
  targetY: props.targetY,
  targetPosition: props.targetPosition,
  curvature: 0.28,
}))

function insertNode(event?: MouseEvent) {
  window.dispatchEvent(new CustomEvent('workflow-edge-add', { detail: { edgeId: props.id, clientX: event?.clientX, clientY: event?.clientY } }))
}

function deleteEdge() {
  window.dispatchEvent(new CustomEvent('workflow-edge-delete', { detail: { edgeId: props.id } }))
}
</script>

<template>
  <BaseEdge
    :id="id"
    :path="path[0]"
    :marker-start="markerStart"
    :marker-end="markerEnd"
    :interaction-width="20"
    :style="style"
    class="workflow-edge-path"
    :class="{ selected, connected: connectedToSelection, active: data?.runtimeStatus === 'active', skipped: data?.runtimeStatus === 'skipped' }"
  />
  <EdgeLabelRenderer>
    <div
      class="workflow-edge-actions nodrag nopan"
      :class="{ selected, connected: connectedToSelection }"
      :style="{ transform: `translate(-50%, -50%) translate(${path[1]}px, ${path[2]}px)` }"
    >
      <span v-if="branchLabel" class="edge-branch-label max-w-32 truncate" :class="sourceHandleId === 'true' ? 'text-emerald-600' : sourceHandleId === 'false' ? 'text-amber-600' : 'text-orange-600'">{{ branchLabel }}</span>
      <button type="button" class="edge-action edge-insert" :aria-label="t('designer.insertNodeOnEdge')" @click.stop="insertNode($event)">
        <Plus :size="12" />
      </button>
      <button v-if="selected" type="button" class="edge-action edge-delete" :aria-label="t('designer.deleteEdge')" @click.stop="deleteEdge">
        <Trash2 :size="11" />
      </button>
    </div>
  </EdgeLabelRenderer>
</template>

<style scoped>
.workflow-edge-actions { position: absolute; z-index: 8; display: flex; align-items: center; gap: 4px; pointer-events: all; }
.edge-branch-label { border: 1px solid var(--border); border-radius: 999px; background: var(--panel); padding: 2px 6px; font-size: 9px; font-weight: 700; box-shadow: 0 1px 4px rgb(16 24 40 / 8%); }
.edge-action { display: flex; width: 20px; height: 20px; align-items: center; justify-content: center; border: 1px solid var(--border); border-radius: 50%; background: var(--panel); color: var(--muted); box-shadow: 0 2px 6px rgb(16 24 40 / 12%); transition: opacity .15s ease, border-color .15s ease, color .15s ease, transform .15s ease; }
.edge-insert { opacity: .18; }
.workflow-edge-actions:hover .edge-insert, .workflow-edge-actions.selected .edge-insert, .edge-insert:focus-visible { border-color: var(--primary); color: var(--primary); opacity: 1; transform: scale(1.08); }
.workflow-edge-actions.connected .edge-insert { border-color: var(--primary); color: var(--primary); opacity: .75; }
.edge-delete { border-color: color-mix(in srgb, #d92d20, transparent 55%); color: #d92d20; }
.edge-delete:hover { background: #fef3f2; }
:global(.dark) .edge-delete:hover { background: rgb(127 29 29 / 25%); }
:global(.workflow-edge-path) { stroke: #98a2b3; stroke-width: 1.5; transition: stroke .15s ease, stroke-width .15s ease; }
:global(.workflow-edge-path.connected) { stroke: var(--primary); stroke-width: 2; stroke-dasharray: 5 4; }
:global(.workflow-edge-path.selected) { stroke: var(--primary); stroke-width: 2; stroke-dasharray: none; }
:global(.workflow-edge-path.active) { stroke: #12b76a; stroke-width: 2.5; stroke-dasharray: none; filter: drop-shadow(0 0 3px rgb(18 183 106 / 28%)); }:global(.workflow-edge-path.skipped) { stroke: #d0d5dd; stroke-dasharray: 4 4; opacity: .42; }
</style>
