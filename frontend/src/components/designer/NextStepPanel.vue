<script setup lang="ts">
import { ChevronRight, GitBranch, Plus } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import NodeConfigSection from './NodeConfigSection.vue'

defineProps<{ nodes: any[] }>()
const emit = defineEmits<{ add: []; parallel: [] }>()
const { t } = useI18n()
</script>

<template>
  <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.nextStep')" :hint="t('designer.connectHint')" :count="nodes.length" collapsible>
    <template #actions><button type="button" class="icon-button" :title="t('designer.addNextNode')" @click="emit('add')"><Plus :size="14" /></button></template>
    <div class="space-y-2">
      <div v-for="node in nodes" :key="node.id" class="flex items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-2.5 text-xs">
        <span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-[var(--primary-soft)] text-[var(--primary)]"><ChevronRight :size="14" /></span>
        <span class="min-w-0 flex-1"><span class="block truncate font-medium">{{ node.data?.label }}</span><span class="muted mt-0.5 block text-[10px]">{{ t(`workflow.nodes.${node.data?.nodeType || node.type}`) }}</span></span>
      </div>
      <button v-if="!nodes.length" type="button" class="flex w-full items-center gap-2 rounded-lg border border-dashed border-[var(--border)] p-3 text-left text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="emit('add')"><span class="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--primary-soft)]"><Plus :size="13" /></span>{{ t('designer.addNextNode') }}</button>
      <button v-else type="button" class="flex w-full items-center gap-2 rounded-lg border border-dashed border-[var(--border)] p-2.5 text-left text-xs text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="emit('parallel')"><span class="flex h-6 w-6 items-center justify-center rounded-md bg-[var(--primary-soft)]"><GitBranch :size="13" /></span>{{ t('designer.addParallelNode') }}</button>
    </div>
  </NodeConfigSection>
</template>
