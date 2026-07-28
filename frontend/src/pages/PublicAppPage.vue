<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { Play } from 'lucide-vue-next'
import { useRoute } from 'vue-router'
import axios from 'axios'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import FormField from '@/components/ui/FormField.vue'
import WorkflowInputField from '@/components/WorkflowInputField.vue'
import WorkflowOutputRenderer from '@/components/WorkflowOutputRenderer.vue'
import { coerceWorkflowInputValues, createWorkflowInputValues } from '@/utils/workflowInputs'
import { consumeRunEvents } from '@/api/runEvents'

const { t } = useI18n()
const route = useRoute()
const app = ref<any>(null)
const values = ref<Record<string, any>>({})
const apiKey = ref('')
const loading = ref(false)
const result = ref<any>(null)
const error = ref('')
const slug = String(route.params.slug)
const headers = (): Record<string, string> => apiKey.value ? { Authorization: `Bearer ${apiKey.value}` } : {}

async function load() {
  try {
    app.value = (await axios.get(`/v1/apps/${slug}`)).data
    values.value = createWorkflowInputValues(app.value.input_fields)
  } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) }
}

async function upload(field: any, event: Event) {
  const input = event.target as HTMLInputElement
  const files = Array.from(input.files || [])
  if (!files.length) return
  loading.value = true
  try {
    const uploaded = []
    for (const file of files) {
      const data = new FormData()
      data.append('file', file)
      uploaded.push((await axios.post(`/v1/apps/${slug}/files`, data, { headers: headers() })).data)
    }
    values.value[field.name] = field.type === 'files' ? uploaded : uploaded[0]
  } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) }
  finally { loading.value = false }
}

async function run() {
  loading.value = true; error.value = ''; result.value = null
  try {
    const inputs = coerceWorkflowInputValues(app.value.input_fields, values.value)
    result.value = (await axios.post(`/v1/apps/${slug}/run`, { inputs }, { headers: { ...headers(), 'Content-Type': 'application/json' } })).data
    let streamedText = ''
    await consumeRunEvents(`/v1/apps/${slug}/runs/${result.value.run_id}/events`, event => {
      if (event.type === 'token') {
        streamedText += String(event.delta || '')
        result.value = { ...result.value, status: 'running', outputs: { text: streamedText } }
      } else if (event.status && ['run_started', 'run_finished'].includes(String(event.type))) result.value = { ...result.value, status: event.status }
    }, headers())
    result.value = (await axios.get(`/v1/apps/${slug}/runs/${result.value.run_id}`, { headers: headers() })).data
  } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) }
  finally { loading.value = false }
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-[var(--app-bg)] px-5 py-10">
    <main class="mx-auto max-w-2xl">
      <div class="mb-7 flex items-center gap-3"><span class="flex h-11 w-11 items-center justify-center rounded-lg bg-[var(--primary)] font-bold text-white">O</span><div><h1 class="text-xl font-semibold">{{ app?.name || t('common.loading') }}</h1><p class="muted mt-1 text-sm">{{ app?.description }}</p></div></div>
      <form v-if="app?.triggers?.includes('form')" class="surface rounded-xl p-6 shadow-sm" @submit.prevent="run">
        <FormField v-if="app.access === 'protected'" class="mb-5" label="API Key" required><InputText v-model="apiKey" type="password" required /></FormField>
        <div class="space-y-5">
          <WorkflowInputField v-for="field in app.input_fields" :key="field.name" v-model="values[field.name]" :field="field" :uploading="loading" @file-change="upload(field, $event)" />
        </div>
        <Button class="mt-6 w-full" type="submit" :loading="loading"><Play :size="16" />{{ t('publicApp.run') }}</Button>
        <AlertBanner :message="error" tone="error" />
        <WorkflowOutputRenderer v-if="result" class="mt-4" :output="result.outputs" />
      </form>
      <div v-else-if="app" class="surface rounded-xl p-8 text-center text-sm text-[var(--muted)]">{{ t('publicApp.formDisabled') }}</div>
      <AlertBanner :message="error" tone="error" />
    </main>
  </div>
</template>
