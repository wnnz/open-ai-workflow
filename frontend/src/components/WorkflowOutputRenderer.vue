<script setup lang="ts">
import { computed } from 'vue'
import { Download } from 'lucide-vue-next'
import { collectWorkflowImages, compactWorkflowOutput } from '@/utils/workflowOutput'

const props = defineProps<{ output: unknown }>()
const images = computed(() => collectWorkflowImages(props.output))
const formatted = computed(() => JSON.stringify(compactWorkflowOutput(props.output), null, 2))
</script>

<template>
  <div class="space-y-4">
    <div v-if="images.length" class="grid grid-cols-1 gap-3 sm:grid-cols-2">
      <figure v-for="(image, index) in images" :key="`${index}-${image.slice(0, 48)}`" class="group relative overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]">
        <a :href="image" target="_blank" rel="noopener noreferrer" class="block aspect-square">
          <img :src="image" :alt="`${$t('designer.generatedImage')} ${Number(index) + 1}`" class="h-full w-full object-contain" loading="lazy" referrerpolicy="no-referrer">
        </a>
        <a :href="image" :download="`generated-image-${Number(index) + 1}`" class="absolute right-2 top-2 flex h-8 w-8 items-center justify-center rounded-md border border-white/70 bg-white/90 text-slate-700 opacity-0 shadow-sm transition hover:bg-white group-hover:opacity-100 focus:opacity-100" :title="$t('common.download')" :aria-label="$t('common.download')">
          <Download :size="15" />
        </a>
      </figure>
    </div>
    <pre class="overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-[11px] leading-5 text-slate-100">{{ formatted }}</pre>
  </div>
</template>
