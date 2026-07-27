<script setup lang="ts">
import { computed, ref } from 'vue'
import { Handle, Position, type NodeProps } from '@vue-flow/core'
import { Play, Plus, RefreshCw, Repeat2, Trash2 } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import NodeValidationBadge from '@/components/designer/NodeValidationBadge.vue'

const props = defineProps<NodeProps>()
const { t } = useI18n()
const menuOpen = ref(false)
const nodeType = computed(() => String(props.data?.nodeType || props.type))
const isLoop = computed(() => nodeType.value === 'loop')
const icon = computed(() => isLoop.value ? RefreshCw : Repeat2)
const validationMessages = computed<string[]>(() => Array.isArray(props.data?.validationMessages) ? props.data.validationMessages : [])
function focusValidation() { window.dispatchEvent(new CustomEvent('workflow-node-validation', { detail: { nodeId: props.id } })) }

function addInside(event?: MouseEvent) {
  window.dispatchEvent(new CustomEvent('workflow-container-add', { detail: { parentId: props.id, clientX: event?.clientX, clientY: event?.clientY } }))
}
function quickAdd(event?: MouseEvent) {
  window.dispatchEvent(new CustomEvent('workflow-quick-add', { detail: { sourceId: props.id, clientX: event?.clientX, clientY: event?.clientY } }))
}
function removeContainer() {
  window.dispatchEvent(new CustomEvent('workflow-container-delete', { detail: { parentId: props.id } }))
}
</script>

<template>
  <section class="workflow-container" :class="[{ selected }, isLoop ? 'is-loop' : 'is-iteration']">
    <NodeValidationBadge :messages="validationMessages" @focus="focusValidation" />
    <Handle type="target" :position="Position.Left" />
    <header class="container-header">
      <span class="container-icon"><component :is="icon" :size="15" /></span>
      <div class="min-w-0 flex-1">
        <div class="truncate text-xs font-semibold">{{ data?.label }}</div>
        <div class="muted mt-0.5 text-[9px]">{{ isLoop ? t('designer.loopContainerHint') : t('designer.iterationContainerHint') }}</div>
      </div>
      <div class="relative">
        <button class="node-menu" type="button" :aria-label="t('designer.more')" @click.stop="menuOpen = !menuOpen">...</button>
        <div v-if="menuOpen" class="surface absolute right-0 top-6 z-30 w-28 rounded-md p-1 shadow-xl">
          <button class="flex w-full items-center gap-2 rounded px-2 py-1.5 text-xs text-red-600 hover:bg-red-50" @click.stop="removeContainer"><Trash2 :size="13" />{{ t('common.delete') }}</button>
        </div>
      </div>
    </header>
    <div class="container-body">
      <div class="container-start"><span><Play :size="12" fill="currentColor" /></span>{{ isLoop ? t('designer.loopStart') : t('designer.iterationStart') }}</div>
      <button class="container-add nodrag" type="button" @click.stop="addInside($event)"><Plus :size="14" />{{ t('designer.addInnerNode') }}</button>
    </div>
    <Handle type="source" :position="Position.Right" class="quick-add-handle">
      <button type="button" :aria-label="t('workflow.addNode')" @click.stop="quickAdd($event)"><Plus :size="12" :stroke-width="2.4" /></button>
    </Handle>
  </section>
</template>

<style scoped>
.workflow-container { position: relative; width: 100%; height: 100%; min-width: 500px; min-height: 250px; overflow: visible; border: 1px solid var(--border); border-radius: 8px; background: color-mix(in srgb, var(--panel), transparent 8%); color: var(--text); box-shadow: 0 3px 14px rgb(16 24 40 / 5%); transition: border-color .15s ease, box-shadow .15s ease; }
.workflow-container:hover, .workflow-container.selected { border-color: var(--container-color); box-shadow: 0 0 0 2px color-mix(in srgb, var(--container-color), transparent 82%), 0 5px 18px rgb(16 24 40 / 7%); }
.container-header { display: flex; height: 52px; align-items: center; gap: 9px; border-bottom: 1px solid var(--border); padding: 0 12px; background: color-mix(in srgb, var(--container-color), transparent 94%); }
.container-icon { display: flex; width: 27px; height: 27px; align-items: center; justify-content: center; border-radius: 6px; background: color-mix(in srgb, var(--container-color), transparent 86%); color: var(--container-color); }
.container-body { position: absolute; inset: 52px 0 0; background-image: radial-gradient(circle, var(--border) 1px, transparent 1px); background-size: 18px 18px; }
.container-start { position: absolute; left: 20px; top: 74px; display: flex; height: 34px; align-items: center; gap: 7px; border: 1px solid var(--border); border-radius: 7px; background: var(--panel); padding: 0 10px; color: var(--muted); font-size: 10px; font-weight: 600; box-shadow: 0 2px 7px rgb(16 24 40 / 6%); }
.container-start span { display: flex; width: 20px; height: 20px; align-items: center; justify-content: center; border-radius: 5px; background: color-mix(in srgb, var(--container-color), transparent 88%); color: var(--container-color); }
.container-add { position: absolute; left: 117px; top: 74px; display: flex; height: 34px; align-items: center; gap: 6px; border: 1px dashed color-mix(in srgb, var(--container-color), transparent 45%); border-radius: 7px; background: var(--panel); padding: 0 11px; color: var(--container-color); font-size: 10px; font-weight: 600; }
.container-add:hover { border-style: solid; background: color-mix(in srgb, var(--container-color), transparent 94%); }
.node-menu { width: 20px; height: 20px; border-radius: 5px; color: var(--muted); font-size: 13px; line-height: 12px; }.node-menu:hover { background: var(--panel-subtle); }
.quick-add-handle button { display: flex; width: 20px; height: 20px; padding: 0; align-items: center; justify-content: center; border: 1px solid var(--primary); border-radius: 50%; background: var(--panel); color: var(--primary); line-height: 0; box-shadow: 0 1px 3px rgb(16 24 40 / 12%); }.quick-add-handle button:hover { background: var(--primary); color: white; }
.is-iteration { --container-color: #155eef; }.is-loop { --container-color: #7f56d9; }
</style>
