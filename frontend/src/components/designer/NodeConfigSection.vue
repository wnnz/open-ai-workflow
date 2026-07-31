<script setup lang="ts">
import { computed, ref } from 'vue'
import { ArrowDownToLine, ArrowUpFromLine, Braces, ChevronDown, Route, ShieldAlert, SlidersHorizontal } from 'lucide-vue-next'

export type NodeConfigSectionKind = 'default' | 'parameters' | 'input' | 'output' | 'flow' | 'policy' | 'advanced'

const props = withDefaults(defineProps<{
  title: string
  hint?: string
  count?: string | number
  collapsible?: boolean
  defaultExpanded?: boolean
  kind?: NodeConfigSectionKind
}>(), { collapsible: false, defaultExpanded: true, kind: 'default' })

const emit = defineEmits<{ toggle: [expanded: boolean] }>()

const expanded = ref(props.defaultExpanded)
const sectionIcon = computed(() => ({
  parameters: SlidersHorizontal,
  input: ArrowDownToLine,
  output: ArrowUpFromLine,
  flow: Route,
  policy: ShieldAlert,
  advanced: Braces,
} as const)[props.kind as Exclude<NodeConfigSectionKind, 'default'>] || null)

function toggle() {
  if (!props.collapsible) return
  expanded.value = !expanded.value
  emit('toggle', expanded.value)
}
</script>

<template>
  <section class="node-config-section" :class="`section-${kind}`" :data-section-kind="kind">
    <div class="section-heading flex items-start gap-2.5">
      <button v-if="collapsible" type="button" class="section-heading-main focus-ring min-w-0 flex-1 text-left" :aria-expanded="expanded" @click="toggle">
        <span v-if="$slots.icon || sectionIcon" class="section-icon"><slot name="icon"><component :is="sectionIcon" :size="14" /></slot></span>
        <span class="min-w-0 flex-1">
          <span class="flex items-center gap-2"><span class="section-title">{{ title }}</span><span v-if="count !== undefined" class="section-count">{{ count }}</span></span>
          <span v-if="hint" class="muted mt-1 block text-[10px] leading-4">{{ hint }}</span>
        </span>
      </button>
      <div v-else class="section-heading-main min-w-0 flex-1">
        <span v-if="$slots.icon || sectionIcon" class="section-icon"><slot name="icon"><component :is="sectionIcon" :size="14" /></slot></span>
        <span class="min-w-0 flex-1"><span class="flex items-center gap-2"><h3 class="section-title">{{ title }}</h3><span v-if="count !== undefined" class="section-count">{{ count }}</span></span><p v-if="hint" class="muted mt-1 text-[10px] leading-4">{{ hint }}</p></span>
      </div>
      <div v-if="$slots.actions" class="shrink-0"><slot name="actions" /></div>
      <button v-if="collapsible" type="button" class="section-chevron focus-ring" :aria-expanded="expanded" :aria-label="expanded ? $t('designer.collapseSection') : $t('designer.expandSection')" @click="toggle"><ChevronDown :size="14" class="transition-transform" :class="expanded && 'rotate-180'" /></button>
    </div>
    <div v-if="!collapsible || expanded" class="section-content mt-3"><slot /></div>
  </section>
</template>

<style scoped>
.node-config-section { --section-accent: var(--primary); }
.section-parameters { --section-accent: #e11d48; }
.section-input { --section-accent: #0284c7; }
.section-output { --section-accent: #059669; }
.section-flow { --section-accent: #7c3aed; }
.section-policy { --section-accent: #d97706; }
.section-advanced { --section-accent: #64748b; }
.section-default > .section-heading { align-items: center; }
.section-default > .section-content { margin-top: 10px; }
.section-heading-main { display: flex; align-items: flex-start; gap: 10px; border: 0; background: transparent; padding: 0; color: inherit; }
button.section-heading-main { cursor: pointer; border-radius: 7px; }
.section-icon { display: flex; width: 28px; height: 28px; flex: none; align-items: center; justify-content: center; border: 1px solid color-mix(in srgb, var(--section-accent), transparent 72%); border-radius: 7px; background: color-mix(in srgb, var(--section-accent), transparent 90%); color: var(--section-accent); }
.section-title { font-size: 12px; font-weight: 650; line-height: 18px; letter-spacing: 0; }
.section-count { min-width: 20px; border-radius: 5px; background: color-mix(in srgb, var(--section-accent), transparent 90%); padding: 2px 6px; color: var(--section-accent); font-size: 9px; font-weight: 650; line-height: 14px; text-align: center; }
.section-chevron { display: flex; width: 28px; height: 28px; flex: none; align-items: center; justify-content: center; border: 0; border-radius: 7px; background: transparent; color: var(--muted); }
.section-chevron:hover { background: var(--panel-subtle); color: var(--text); }
</style>
