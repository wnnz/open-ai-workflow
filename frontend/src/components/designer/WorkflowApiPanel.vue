<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(defineProps<{
  origin: string
  slug?: string
  triggers?: string[]
}>(), {
  slug: '',
  triggers: () => [],
})

const { t } = useI18n()
const appBaseUrl = computed(() => `${props.origin}/v1/apps/${props.slug}`)
</script>

<template>
  <section class="min-h-0 flex-1 overflow-auto p-7">
    <div class="mx-auto max-w-4xl">
      <h2 class="text-xl font-semibold">{{ t('designer.apiTitle') }}</h2>
      <p class="muted mt-1 text-sm">{{ t('designer.apiHint') }}</p>
      <div class="surface mt-5 rounded-lg p-5">
        <div class="text-xs font-semibold">{{ t('designer.endpoints') }}</div>
        <div class="mt-2 space-y-2">
          <code v-if="triggers.includes('form')" class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">GET {{ origin }}/apps/{{ slug }}</code>
          <code v-if="triggers.includes('api')" class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">POST {{ appBaseUrl }}/run</code>
          <code v-if="triggers.includes('webhook')" class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">POST {{ appBaseUrl }}/webhook</code>
          <code class="block rounded-md bg-slate-950 p-3 text-xs text-slate-100">POST {{ appBaseUrl }}/files</code>
        </div>
        <div class="mt-5 text-xs font-semibold">cURL</div>
        <pre class="mt-2 overflow-auto rounded-md bg-slate-950 p-4 text-xs text-slate-100">curl -X POST '{{ appBaseUrl }}/run' \
  -H 'Content-Type: application/json' \
  -d '{"inputs":{"message":"Hello"}}'</pre>
      </div>
    </div>
  </section>
</template>
