<script setup lang="ts">
import RunHistoryPopover from './RunHistoryPopover.vue'

export type WorkflowRunSummary = {
  id: string
  created_at: string
  triggered_by?: string | null
  status: string
}

withDefaults(defineProps<{ runs: WorkflowRunSummary[]; detailOpen?: boolean; selectedRunId?: string }>(), { detailOpen: false, selectedRunId: '' })
const emit = defineEmits<{ refresh: []; replay: [run: WorkflowRunSummary] }>()
</script>

<template>
  <section class="min-h-0 flex-1 overflow-y-auto px-4 py-5 transition-[padding] sm:p-7" :class="detailOpen && 'xl:pr-[458px]'">
    <div class="mx-auto w-full max-w-6xl">
      <RunHistoryPopover
        :open="true"
        :runs="runs"
        :selected-run-id="selectedRunId"
        embedded
        @refresh="emit('refresh')"
        @replay="emit('replay', $event)"
      />
    </div>
  </section>
</template>
