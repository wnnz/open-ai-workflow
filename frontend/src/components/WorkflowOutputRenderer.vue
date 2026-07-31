<script setup lang="ts">
import axios from 'axios'
import { computed, ref } from 'vue'
import { Download, FileText } from 'lucide-vue-next'
import { collectWorkflowFiles, collectWorkflowImages, compactWorkflowOutput, type WorkflowFileOutput } from '@/utils/workflowOutput'

const props = withDefaults(defineProps<{ output: unknown; downloadHeaders?: Record<string, string> }>(), { downloadHeaders: () => ({}) })
const images = computed(() => collectWorkflowImages(props.output))
const files = computed(() => collectWorkflowFiles(props.output))
const formatted = computed(() => JSON.stringify(compactWorkflowOutput(props.output), null, 2))
const downloading = ref('')
const downloadError = ref('')

function readableSize(size: number) {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

async function downloadFile(file: WorkflowFileOutput) {
  downloading.value = file.id
  downloadError.value = ''
  try {
    const token = localStorage.getItem('access_token')
    const headers = { ...(token ? { Authorization: `Bearer ${token}` } : {}), ...props.downloadHeaders }
    const response = await axios.get(file.download_url, { headers, responseType: 'blob' })
    const url = URL.createObjectURL(response.data)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = file.filename
    anchor.click()
    URL.revokeObjectURL(url)
  } catch (cause: any) {
    downloadError.value = cause.response?.data?.detail || cause.message || String(cause)
  } finally {
    downloading.value = ''
  }
}
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
    <div v-if="files.length" class="space-y-2">
      <div v-for="file in files" :key="file.id" class="flex items-center gap-3 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
        <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-white text-rose-600 shadow-sm dark:bg-slate-900"><FileText :size="18" /></span>
        <div class="min-w-0 flex-1"><div class="truncate text-xs font-semibold">{{ file.filename }}</div><div class="muted mt-1 text-[10px]">{{ readableSize(file.size) }} · DOCX</div></div>
        <button type="button" class="icon-button" :disabled="downloading === file.id" :title="$t('common.download')" :aria-label="$t('common.download')" @click="downloadFile(file)"><Download :size="16" /></button>
      </div>
      <p v-if="downloadError" class="text-xs text-red-600" role="alert">{{ downloadError }}</p>
    </div>
    <pre class="overflow-auto whitespace-pre-wrap rounded-lg bg-slate-950 p-4 text-[11px] leading-5 text-slate-100">{{ formatted }}</pre>
  </div>
</template>
