<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = defineProps<{ runs: Array<{ status: string }> }>()
const { t } = useI18n()
const succeeded = computed(() => props.runs.filter((run) => run.status === 'succeeded').length)
const failed = computed(() => props.runs.filter((run) => run.status === 'failed').length)
</script>

<template>
  <section class="min-h-0 flex-1 overflow-auto p-7">
    <div class="mx-auto max-w-5xl">
      <h2 class="text-xl font-semibold">{{ t('designer.monitoring') }}</h2>
      <p class="muted mt-1 text-sm">{{ t('designer.monitorHint') }}</p>
      <div class="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div class="surface rounded-lg p-5"><div class="muted text-xs">{{ t('designer.totalRuns') }}</div><div class="mt-2 text-3xl font-semibold">{{ runs.length }}</div></div>
        <div class="surface rounded-lg p-5"><div class="muted text-xs">{{ t('designer.successRuns') }}</div><div class="mt-2 text-3xl font-semibold text-emerald-600">{{ succeeded }}</div></div>
        <div class="surface rounded-lg p-5"><div class="muted text-xs">{{ t('designer.failedRuns') }}</div><div class="mt-2 text-3xl font-semibold text-red-600">{{ failed }}</div></div>
      </div>
    </div>
  </section>
</template>
