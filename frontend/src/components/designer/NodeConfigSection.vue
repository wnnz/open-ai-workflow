<script setup lang="ts">
import { ref } from 'vue'
import { ChevronDown } from 'lucide-vue-next'

const props = withDefaults(defineProps<{
  title: string
  hint?: string
  count?: string | number
  collapsible?: boolean
  defaultExpanded?: boolean
}>(), { collapsible: false, defaultExpanded: true })

const expanded = ref(props.defaultExpanded)
function toggle() { if (props.collapsible) expanded.value = !expanded.value }
</script>

<template>
  <section>
    <div class="flex items-start gap-3">
      <button v-if="collapsible" type="button" class="min-w-0 flex-1 text-left" :aria-expanded="expanded" @click="toggle">
        <span class="flex items-center gap-2"><span class="text-xs font-semibold">{{ title }}</span><span v-if="count !== undefined" class="muted rounded bg-[var(--panel-subtle)] px-1.5 py-0.5 text-[9px]">{{ count }}</span></span>
        <span v-if="hint" class="muted mt-1 block text-[11px] leading-4">{{ hint }}</span>
      </button>
      <div v-else class="min-w-0 flex-1"><h3 class="text-xs font-semibold">{{ title }}</h3><p v-if="hint" class="muted mt-1 text-[11px] leading-4">{{ hint }}</p></div>
      <div v-if="$slots.actions" class="shrink-0"><slot name="actions" /></div>
      <button v-if="collapsible" type="button" class="icon-button -mr-1 -mt-1" :aria-label="expanded ? $t('designer.collapseSection') : $t('designer.expandSection')" @click="toggle"><ChevronDown :size="14" class="transition-transform" :class="expanded && 'rotate-180'" /></button>
    </div>
    <div v-if="!collapsible || expanded" class="mt-3"><slot /></div>
  </section>
</template>
