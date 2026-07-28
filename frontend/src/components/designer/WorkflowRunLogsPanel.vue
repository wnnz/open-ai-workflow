<script setup lang="ts">
import { Activity } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Button from '@/volt/Button.vue'

export type WorkflowRunSummary = {
  id: string
  created_at: string
  triggered_by?: string | null
  status: string
}

defineProps<{ runs: WorkflowRunSummary[] }>()
const emit = defineEmits<{ refresh: [] }>()
const { t } = useI18n()
</script>

<template>
  <section class="min-h-0 flex-1 overflow-auto p-7">
    <div class="mx-auto max-w-5xl">
      <div class="flex items-center">
        <div><h2 class="text-xl font-semibold">{{ t('designer.runLogs') }}</h2><p class="muted mt-1 text-sm">{{ t('designer.logsHint') }}</p></div>
        <Button class="ml-auto" variant="secondary" @click="emit('refresh')"><Activity :size="15" />{{ t('common.refresh') }}</Button>
      </div>
      <div class="surface mt-5 overflow-hidden rounded-lg">
        <div v-for="item in runs" :key="item.id" class="grid grid-cols-[160px_110px_120px_minmax(0,1fr)] border-b border-[var(--border)] px-4 py-3 text-sm last:border-0">
          <span>{{ new Date(item.created_at).toLocaleString() }}</span>
          <span>{{ t(`designer.triggerShort.${item.triggered_by || 'studio'}`) }}</span>
          <span :class="item.status === 'succeeded' ? 'text-emerald-600' : 'text-red-600'">{{ item.status }}</span>
          <span class="truncate font-mono text-xs">{{ item.id }}</span>
        </div>
        <div v-if="!runs.length" class="muted py-16 text-center text-sm">{{ t('designer.noRun') }}</div>
      </div>
    </div>
  </section>
</template>
