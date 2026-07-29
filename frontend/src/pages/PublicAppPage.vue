<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { LockKeyhole, LogIn, Play, User } from 'lucide-vue-next'
import { useRoute, useRouter } from 'vue-router'
import axios from 'axios'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import FormField from '@/components/ui/FormField.vue'
import WorkflowInputField from '@/components/WorkflowInputField.vue'
import WorkflowOutputRenderer from '@/components/WorkflowOutputRenderer.vue'
import { coerceWorkflowInputValues, createWorkflowInputValues } from '@/utils/workflowInputs'
import { consumeRunEvents } from '@/api/runEvents'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()
const auth = useAuthStore()
const app = ref<any>(null)
const values = ref<Record<string, any>>({})
const accessReady = ref(false)
const accessPassword = ref('')
const appAccessToken = ref('')
const loading = ref(false)
const result = ref<any>(null)
const error = ref('')
const slug = String(route.params.slug)
const terminalStatuses = new Set(['succeeded', 'failed', 'waiting'])
let activeRunId = ''
const headers = (): Record<string, string> => {
  if (appAccessToken.value) return { 'X-App-Access': appAccessToken.value }
  if (app.value?.access === 'protected' && auth.token) return { Authorization: `Bearer ${auth.token}` }
  return {}
}
const runStorageKey = () => app.value?.access === 'protected'
  ? `weaverun:public-run:${slug}:${auth.user?.id || 'anonymous'}`
  : `weaverun:public-run:${slug}`
const running = computed(() => Boolean(result.value && !terminalStatuses.has(result.value.status)))

async function redirectToLogin() {
  await router.replace({ path: '/login', query: { redirect: route.fullPath } })
}

async function initializeForm() {
  accessReady.value = true
  values.value = createWorkflowInputValues(app.value.input_fields)
  await restoreRun()
}

async function authorizeStoredPassword() {
  const stored = sessionStorage.getItem(`weaverun:app-access:${slug}`)
  if (!stored) return false
  try {
    await axios.post(`/v1/apps/${slug}/access`, {}, { headers: { 'X-App-Access': stored } })
    appAccessToken.value = stored
    await initializeForm()
    return true
  } catch {
    sessionStorage.removeItem(`weaverun:app-access:${slug}`)
    return false
  }
}

async function authorizeSignedInUser() {
  if (!auth.authenticated) return false
  try {
    await auth.refresh()
    await axios.post(`/v1/apps/${slug}/access`, {}, { headers: { Authorization: `Bearer ${auth.token}` } })
    await initializeForm()
    return true
  } catch (cause: any) {
    if (cause.response?.status === 401) auth.logout()
    return false
  }
}

async function unlockWithPassword() {
  if (!accessPassword.value || loading.value) return
  loading.value = true; error.value = ''
  try {
    const { data } = await axios.post(`/v1/apps/${slug}/access`, { password: accessPassword.value })
    appAccessToken.value = data.access_token
    sessionStorage.setItem(`weaverun:app-access:${slug}`, data.access_token)
    accessPassword.value = ''
    await initializeForm()
  } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) }
  finally { loading.value = false }
}

function delay(milliseconds: number) {
  return new Promise(resolve => window.setTimeout(resolve, milliseconds))
}

async function getRun(runId: string) {
  return (await axios.get(`/v1/apps/${slug}/runs/${runId}`, { headers: headers() })).data
}

async function followRun(runId: string) {
  try {
    let streamedText = ''
    await consumeRunEvents(`/v1/apps/${slug}/runs/${runId}/events`, event => {
      if (activeRunId !== runId) return
      if (event.type === 'token') {
        streamedText += String(event.delta || '')
        result.value = { ...result.value, status: 'running', outputs: { text: streamedText } }
      } else if (event.status && ['run_started', 'run_finished'].includes(String(event.type))) {
        result.value = { ...result.value, status: event.status }
      }
    }, headers())
  } catch {
    // A dropped event stream is recoverable; persisted run state remains authoritative.
  }

  while (activeRunId === runId) {
    const current = await getRun(runId)
    if (activeRunId !== runId) return
    result.value = current
    if (terminalStatuses.has(current.status)) {
      if (current.status === 'failed') error.value = current.error || t('publicApp.runFailed')
      return
    }
    await delay(1500)
  }
}

async function restoreRun() {
  const storageKey = runStorageKey()
  const runId = sessionStorage.getItem(storageKey)
  if (!runId) return
  activeRunId = runId
  loading.value = true
  try {
    result.value = await getRun(runId)
    if (!terminalStatuses.has(result.value.status)) await followRun(runId)
  } catch {
    sessionStorage.removeItem(storageKey)
    result.value = null
  } finally {
    if (activeRunId === runId) loading.value = false
  }
}

async function load() {
  try {
    app.value = (await axios.get(`/v1/apps/${slug}`)).data
    if (app.value.access !== 'protected') return await initializeForm()
    if (app.value.access_options?.password && await authorizeStoredPassword()) return
    if (app.value.access_options?.login && await authorizeSignedInUser()) return
    if (app.value.access_options?.login && !app.value.access_options?.password && !auth.authenticated) {
      return await redirectToLogin()
    }
    if (!app.value.access_options?.login && !app.value.access_options?.password) {
      error.value = t('publicApp.noActiveAccess')
    }
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
  if (loading.value) return
  loading.value = true; error.value = ''; result.value = null
  let runId = ''
  try {
    const inputs = coerceWorkflowInputValues(app.value.input_fields, values.value)
    const created = (await axios.post(`/v1/apps/${slug}/form`, { inputs }, { headers: { ...headers(), 'Content-Type': 'application/json' } })).data
    runId = String(created.run_id)
    activeRunId = runId
    result.value = created
    sessionStorage.setItem(runStorageKey(), runId)
    await followRun(runId)
  } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) }
  finally { if (!runId || activeRunId === runId) loading.value = false }
}

onMounted(load)
</script>

<template>
  <div class="min-h-screen bg-[var(--app-bg)] px-5 py-10">
    <main class="mx-auto max-w-2xl">
      <div class="mb-7 flex flex-wrap items-center justify-between gap-3">
        <div class="flex min-w-0 items-center gap-3"><span class="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-[var(--primary)] font-bold text-white">O</span><div class="min-w-0"><h1 class="text-xl font-semibold">{{ app?.name || t('common.loading') }}</h1><p class="muted mt-1 text-sm">{{ app?.description }}</p></div></div>
        <div v-if="app?.access === 'protected' && auth.user" class="flex items-center gap-2 text-sm text-[var(--muted)]"><User :size="16" /><span>{{ t('publicApp.signedInAs', { name: auth.user.display_name }) }}</span></div>
      </div>
      <form v-if="app?.triggers?.includes('form') && accessReady" class="surface rounded-xl p-6 shadow-sm" @submit.prevent="run">
        <div class="space-y-5">
          <WorkflowInputField v-for="field in app.input_fields" :key="field.name" v-model="values[field.name]" :field="field" :uploading="loading" @file-change="upload(field, $event)" />
        </div>
        <Button class="mt-6 w-full" type="submit" :loading="loading" :disabled="loading"><Play :size="16" />{{ t('publicApp.run') }}</Button>
        <AlertBanner v-if="running" :message="t('publicApp.running')" tone="info" />
        <AlertBanner v-else-if="result?.status === 'waiting'" :message="t('publicApp.waiting')" tone="info" />
        <WorkflowOutputRenderer v-if="result?.status === 'succeeded'" class="mt-4" :output="result.outputs" />
      </form>
      <section v-else-if="app?.triggers?.includes('form') && app?.access === 'protected'" class="surface rounded-xl p-6 shadow-sm">
        <div class="flex items-center gap-3"><span class="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><LockKeyhole :size="18" /></span><div><h2 class="text-sm font-semibold">{{ t('publicApp.protectedTitle') }}</h2><p class="muted mt-0.5 text-xs">{{ t('publicApp.protectedHint') }}</p></div></div>
        <Button v-if="app.access_options?.login && !auth.authenticated" class="mt-5 w-full" variant="secondary" @click="redirectToLogin"><LogIn :size="16" />{{ t('publicApp.signIn') }}</Button>
        <form v-if="app.access_options?.password" class="mt-5" @submit.prevent="unlockWithPassword"><FormField :label="t('publicApp.accessPassword')" required><InputText v-model="accessPassword" type="password" autocomplete="current-password" required /></FormField><Button class="mt-3 w-full" type="submit" :loading="loading"><LockKeyhole :size="15" />{{ t('publicApp.unlock') }}</Button></form>
      </section>
      <div v-else-if="app" class="surface rounded-xl p-8 text-center text-sm text-[var(--muted)]">{{ t('publicApp.formDisabled') }}</div>
      <AlertBanner :message="error" tone="error" />
    </main>
  </div>
</template>
