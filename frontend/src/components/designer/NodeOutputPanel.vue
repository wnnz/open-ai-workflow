<script setup lang="ts">
import { computed } from 'vue'
import { Check, Copy } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import { getNodeOutputVariables } from '@/utils/workflowVariables'
import NodeConfigSection from './NodeConfigSection.vue'

const props = withDefaults(defineProps<{ node: any; copiedPath?: string }>(), { copiedPath: '' })
const emit = defineEmits<{ copy: [path: string] }>()
const { t } = useI18n()
const variables = computed(() => getNodeOutputVariables(props.node))

function descriptionKey(name: string) {
  const known = new Set(['text', 'files', 'file', 'content', 'status_code', 'body', 'headers', 'url', 'elapsed_ms', 'ok', 'result', 'branch', 'items', 'documents', 'structured_output', 'reasoning_content', 'error_type', 'error_message', '_logs', '_elapsed_ms'])
  return known.has(name) ? name : 'generic'
}
</script>

<template>
  <NodeConfigSection v-if="variables.length" class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.outputVariables')" :count="variables.length" collapsible>
    <div class="overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--panel)]">
      <button v-for="variable in variables" :key="variable.path" type="button" class="grid w-full grid-cols-[minmax(0,1fr)_82px_24px] items-center gap-2 border-b border-[var(--border)] px-3 py-2.5 text-left last:border-0 hover:bg-[var(--panel-subtle)]" :title="t('designer.copyVariable')" @click="emit('copy', variable.path)">
        <span class="min-w-0"><span class="block truncate font-mono text-[11px] font-semibold">{{ variable.label }}</span><span class="muted mt-0.5 block text-[10px] leading-4">{{ t(`designer.outputDescriptions.${descriptionKey(variable.label)}`) }}</span></span>
        <span class="rounded bg-[var(--primary-soft)] px-1.5 py-1 text-center text-[9px] font-medium text-[var(--primary)]">{{ variable.type }}</span>
        <Check v-if="copiedPath === variable.path" :size="13" class="text-emerald-600" /><Copy v-else :size="12" class="muted" />
      </button>
    </div>
  </NodeConfigSection>
</template>
