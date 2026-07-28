<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  CheckCircle2,
  CircleAlert,
  KeyRound,
  Plus,
  RefreshCw,
  Server,
  Trash2,
  Wifi,
} from 'lucide-vue-next'
import api from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import FormField from '@/components/ui/FormField.vue'
import ModalShell from '@/components/ui/ModalShell.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import ModelProviderCard, { type ProviderStatus } from '@/components/models/ModelProviderCard.vue'
import { modelProviderTemplates } from '@/config/modelProviderTemplates'
import { useWorkspacesStore } from '@/stores/workspaces'
import Button from '@/volt/Button.vue'
import ActionCard from '@/volt/ActionCard.vue'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'

type ProviderConfig = {
  api_mode: 'chat_completions' | 'responses'
  timeout_seconds: number
  max_retries: number
  allow_private_network: boolean
  custom_headers: Record<string, string>
  capabilities: Record<string, boolean>
}
type Provider = {
  id: string
  name: string
  provider_type: string
  base_url: string
  default_model: string
  config: ProviderConfig
  has_api_key: boolean
  last_tested_at?: string | null
  last_test_status: ProviderStatus
  last_test_latency_ms?: number | null
  available_models: string[]
}

const { t } = useI18n()
const workspaces = useWorkspacesStore()
const templates = modelProviderTemplates
const items = ref<Provider[]>([])
const loading = ref(false)
const saving = ref(false)
const testing = ref('')
const deleting = ref('')
const showForm = ref(false)
const showDelete = ref(false)
const editing = ref<Provider | null>(null)
const pendingDelete = ref<Provider | null>(null)
const message = ref('')
const error = ref('')
const formError = ref('')
const connectionResult = ref<any>(null)
const availableModels = ref<string[]>([])
const fetchingModels = ref(false)
const verifyInference = ref(false)
const headersJson = ref('{}')

function emptyConfig(privateNetwork = false): ProviderConfig {
  return {
    api_mode: 'chat_completions',
    timeout_seconds: 30,
    max_retries: 1,
    allow_private_network: privateNetwork,
    custom_headers: {},
    capabilities: {
      streaming: true,
      vision: false,
      tools: false,
      structured_output: true,
      embeddings: false,
    },
  }
}
const form = ref({
  name: '',
  provider_type: 'openai-compatible',
  base_url: '',
  api_key: '',
  default_model: '',
  config: emptyConfig(),
})

const canManage = computed(() => ['owner', 'admin'].includes(workspaces.active?.role || ''))
const parsedHeaders = computed(() => {
  try {
    const value = JSON.parse(headersJson.value || '{}')
    return value && typeof value === 'object' && !Array.isArray(value) ? value : null
  } catch {
    return null
  }
})
const baseUrlValid = computed(() => {
  try {
    const url = new URL(form.value.base_url)
    return ['http:', 'https:'].includes(url.protocol) && !url.username && !url.password && !url.hash
  } catch {
    return false
  }
})
const canSave = computed(() => Boolean(
  form.value.name.trim()
  && form.value.default_model.trim()
  && baseUrlValid.value
  && parsedHeaders.value,
))
const canTestDraft = computed(() => canSave.value)
const availableModelOptions = computed(() => availableModels.value.map((model) => ({
  label: model,
  value: model,
})))

function apiError(cause: any) {
  const detail = cause.response?.data?.detail
  if (typeof detail === 'string') return detail
  if (detail?.message) {
    const names = (detail.references || []).map((item: any) => item.name).join('、')
    return names ? `${detail.message}：${names}` : detail.message
  }
  return cause.message || String(cause)
}
function clearFeedback() {
  message.value = ''
  error.value = ''
  formError.value = ''
  connectionResult.value = null
}
function setTemplate(name: string) {
  const template = templates[name]
  form.value.name = name
  form.value.base_url = template.base_url
  form.value.default_model = template.model
  form.value.config.allow_private_network = Boolean(template.privateNetwork)
}
function openCreate(templateName = 'OpenAI') {
  editing.value = null
  form.value = {
    name: '',
    provider_type: 'openai-compatible',
    base_url: '',
    api_key: '',
    default_model: '',
    config: emptyConfig(),
  }
  headersJson.value = '{}'
  availableModels.value = []
  verifyInference.value = false
  clearFeedback()
  setTemplate(templateName)
  showForm.value = true
}
function openEdit(item: Provider) {
  editing.value = item
  form.value = {
    name: item.name,
    provider_type: item.provider_type,
    base_url: item.base_url,
    api_key: '',
    default_model: item.default_model,
    config: {
      ...emptyConfig(),
      ...item.config,
      capabilities: { ...emptyConfig().capabilities, ...(item.config.capabilities || {}) },
      custom_headers: { ...(item.config.custom_headers || {}) },
    },
  }
  headersJson.value = JSON.stringify(form.value.config.custom_headers, null, 2)
  availableModels.value = [...item.available_models]
  verifyInference.value = false
  clearFeedback()
  showForm.value = true
}
function payload() {
  return {
    ...form.value,
    name: form.value.name.trim(),
    base_url: form.value.base_url.trim().replace(/\/+$/, ''),
    default_model: form.value.default_model.trim(),
    config: { ...form.value.config, custom_headers: parsedHeaders.value || {} },
  }
}
async function load() {
  if (!workspaces.activeId) return
  loading.value = true
  error.value = ''
  try {
    items.value = (await api.get(`/workspaces/${workspaces.activeId}/models`)).data
  } catch (cause: any) {
    error.value = apiError(cause)
  } finally {
    loading.value = false
  }
}
async function save() {
  if (!canSave.value) return
  saving.value = true
  formError.value = ''
  try {
    if (editing.value) {
      const data: any = payload()
      if (!data.api_key) delete data.api_key
      await api.patch(`/workspaces/${workspaces.activeId}/models/${editing.value.id}`, data)
      message.value = t('models.updated')
    } else {
      await api.post(`/workspaces/${workspaces.activeId}/models`, payload())
      message.value = t('models.created')
    }
    showForm.value = false
    form.value.api_key = ''
    await load()
  } catch (cause: any) {
    formError.value = apiError(cause)
  } finally {
    saving.value = false
  }
}
async function testDraft() {
  if (!canTestDraft.value) return
  testing.value = 'draft'
  formError.value = ''
  connectionResult.value = null
  try {
    const data: any = { ...payload(), verify_inference: verifyInference.value }
    let path = `/workspaces/${workspaces.activeId}/models/connection-test`
    if (editing.value) {
      path = `/workspaces/${workspaces.activeId}/models/${editing.value.id}/connection-test`
      if (!data.api_key) delete data.api_key
    }
    connectionResult.value = (await api.post(path, data)).data
  } catch (cause: any) {
    formError.value = apiError(cause)
  } finally {
    testing.value = ''
  }
}
async function fetchModels() {
  if (!baseUrlValid.value || !parsedHeaders.value) return
  fetchingModels.value = true
  formError.value = ''
  try {
    const data: any = {
      base_url: form.value.base_url.trim().replace(/\/+$/, ''),
      api_key: form.value.api_key,
      config: { ...form.value.config, custom_headers: parsedHeaders.value },
    }
    let path = `/workspaces/${workspaces.activeId}/models/catalog`
    if (editing.value) {
      path = `/workspaces/${workspaces.activeId}/models/${editing.value.id}/catalog`
      if (!data.api_key) delete data.api_key
    }
    const result = (await api.post(path, data)).data
    availableModels.value = result.models || []
    if (!availableModels.value.length) formError.value = t('models.noModelsReturned')
  } catch (cause: any) {
    formError.value = apiError(cause)
  } finally {
    fetchingModels.value = false
  }
}
async function testSaved(item: Provider, full = false) {
  testing.value = item.id
  clearFeedback()
  try {
    const result = (await api.post(`/workspaces/${workspaces.activeId}/models/${item.id}/test`, { verify_inference: full })).data
    message.value = result.warning || `${result.message} · ${result.latency_ms} ms`
    await load()
  } catch (cause: any) {
    const connectionError = apiError(cause)
    await load()
    error.value = connectionError
  } finally {
    testing.value = ''
  }
}
function requestRemove(item: Provider) {
  pendingDelete.value = item
  showDelete.value = true
}
async function confirmRemove() {
  const item = pendingDelete.value
  if (!item) return
  deleting.value = item.id
  error.value = ''
  try {
    await api.delete(`/workspaces/${workspaces.activeId}/models/${item.id}`)
    message.value = t('models.deleted')
    showDelete.value = false
    pendingDelete.value = null
    await load()
  } catch (cause: any) {
    error.value = apiError(cause)
  } finally {
    deleting.value = ''
  }
}
onMounted(load)
watch(() => workspaces.activeId, load)
</script>

<template>
  <AppShell>
    <main class="mx-auto min-h-screen max-w-7xl px-5 py-6 sm:px-7">
      <PageHeader :title="t('models.title')" :subtitle="t('models.subtitle')">
        <template #actions>
          <Button v-if="canManage" @click="openCreate()"><Plus :size="16" />{{ t('models.add') }}</Button>
        </template>
      </PageHeader>
      <AlertBanner :message="message" tone="success" />
      <AlertBanner :message="error" tone="error" />

      <section class="mt-6" aria-labelledby="configured-providers-heading">
        <div class="flex items-center gap-3">
          <div>
            <h2 id="configured-providers-heading" class="text-sm font-semibold">{{ t('models.configured') }}</h2>
            <p class="muted mt-1 text-xs">{{ t('models.configuredHint') }}</p>
          </div>
          <IconButton class="ml-auto" :label="t('common.refresh')" @click="load"><RefreshCw :size="15" /></IconButton>
        </div>
        <div v-if="loading" class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3" aria-live="polite">
          <div v-for="index in 3" :key="index" class="surface h-48 animate-pulse rounded-xl" />
        </div>
        <div v-else-if="items.length" class="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          <ModelProviderCard
            v-for="item in items"
            :key="item.id"
            :provider="item"
            :can-manage="canManage"
            :testing="testing === item.id"
            :deleting="deleting === item.id"
            @test="testSaved(item)"
            @full-test="testSaved(item, true)"
            @edit="openEdit(item)"
            @remove="requestRemove(item)"
          />
        </div>
        <div v-else class="surface mt-4 rounded-xl">
          <EmptyState :title="t('models.empty')" :description="t('models.emptyHint')" compact>
            <template #icon><Server :size="36" /></template>
          </EmptyState>
        </div>
      </section>

      <section v-if="canManage" class="mt-8 border-t border-[var(--border)] pt-6" aria-labelledby="available-providers-heading">
        <h2 id="available-providers-heading" class="text-sm font-semibold">{{ t('models.available') }}</h2>
        <p class="muted mt-1 text-xs">{{ t('models.availableHint') }}</p>
        <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          <ActionCard v-for="(template, key) in templates" :key="key" class="min-h-28 p-3" @click="openCreate(String(key))">
            <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-sm font-bold text-[var(--primary)]">{{ String(key).slice(0, 2) }}</span>
            <span class="mt-3 block text-sm font-semibold">{{ key }}</span><span class="muted mt-1 block truncate text-[10px]">{{ template.model }}</span>
          </ActionCard>
        </div>
      </section>
    </main>

    <ModalShell v-model="showForm" :title="editing ? t('models.edit') : t('models.add')" max-width="max-w-3xl" form @submit="save">
      <AlertBanner :message="formError" tone="error" />
      <AlertBanner v-if="connectionResult" tone="success">
        {{ connectionResult.warning || connectionResult.message }} · {{ connectionResult.latency_ms }} ms
      </AlertBanner>
      <div class="grid items-start gap-x-5 gap-y-4 sm:grid-cols-2">
        <FormField class="sm:col-span-2" :label="t('common.name')" required><InputText v-model="form.name" required /></FormField>
        <FormField label="Base URL" :error="form.base_url && !baseUrlValid ? t('models.invalidBaseUrl') : ''" required><InputText v-model="form.base_url" required placeholder="https://api.example.com/v1" /></FormField>
        <FormField label="API Key" :hint="editing?.has_api_key ? t('models.apiKeyKeepHint') : t('models.apiKeyOptionalHint')" hint-after><InputText v-model="form.api_key" type="password" autocomplete="new-password" /></FormField>
        <FormField :label="t('models.apiMode')"><Select v-model="form.config.api_mode" :aria-label="t('models.apiMode')" :options-label="t('models.apiMode')"><option value="chat_completions">Chat Completions</option><option value="responses">Responses</option></Select></FormField>
        <div>
          <label class="block text-sm font-medium" for="provider-default-model">{{ t('models.defaultModel') }}<span class="ml-1 text-red-500">*</span></label>
          <span class="mt-1.5 flex gap-2">
            <Select
              id="provider-default-model"
              v-model="form.default_model"
              class="min-w-0 flex-1"
              :options="availableModelOptions"
              editable
              allow-custom-value
              :filter-options="false"
              highlight-matches
              highlight-first-match
              open-on-options-change
              required
              :show-options-label="t('models.showModelOptions')"
              :options-label="t('models.modelOptions')"
            />
            <Button class="h-10 shrink-0" type="button" variant="secondary" :loading="fetchingModels" :disabled="!baseUrlValid || !parsedHeaders" @click="fetchModels">{{ t('models.fetchModels') }}</Button>
          </span>
        </div>
        <FormField :label="t('models.timeout')"><InputText :model-value="String(form.config.timeout_seconds)" type="number" min="1" max="300" @update:model-value="form.config.timeout_seconds = Number($event)" /></FormField>
        <FormField :label="t('models.maxRetries')"><InputText :model-value="String(form.config.max_retries)" type="number" min="0" max="10" @update:model-value="form.config.max_retries = Number($event)" /></FormField>
        <FormField class="sm:col-span-2" :label="t('models.customHeaders')" :hint="t('models.customHeadersHint')" :error="parsedHeaders ? '' : t('models.invalidJson')"><textarea v-model="headersJson" class="focus-ring h-24 w-full rounded-lg border border-[var(--border)] bg-[var(--panel)] p-3 font-mono text-xs" spellcheck="false" /></FormField>
      </div>
      <label class="mt-4 flex items-start gap-2 rounded-lg border border-[var(--border)] p-3 text-xs"><input v-model="form.config.allow_private_network" class="mt-0.5" type="checkbox"><span><span class="block font-semibold">{{ t('models.allowPrivateNetwork') }}</span><span class="muted mt-1 block">{{ t('models.allowPrivateNetworkHint') }}</span></span></label>
      <fieldset class="mt-4 rounded-lg border border-[var(--border)] p-3"><legend class="px-1 text-xs font-semibold">{{ t('models.capabilities') }}</legend><div class="grid gap-2 sm:grid-cols-3"><label v-for="capability in ['streaming','vision','tools','structured_output','embeddings']" :key="capability" class="flex items-center gap-2 text-xs"><input v-model="form.config.capabilities[capability]" type="checkbox">{{ t(`models.capabilityNames.${capability}`) }}</label></div></fieldset>
      <label class="mt-4 flex items-center gap-2 text-xs"><input v-model="verifyInference" type="checkbox">{{ t('models.verifyInference') }}</label>
      <p v-if="editing && editing.has_api_key && !form.api_key" class="muted mt-2 flex items-center gap-1 text-[11px]"><KeyRound :size="13" />{{ t('models.editTestKeyHint') }}</p>
      <p v-if="connectionResult" class="mt-2 flex items-center gap-1 text-xs text-emerald-600"><CheckCircle2 :size="14" />{{ t('models.connectionReady') }}</p>
      <template #footer>
        <Button type="button" variant="secondary" @click="showForm = false">{{ t('common.cancel') }}</Button>
        <Button type="button" variant="secondary" :loading="testing === 'draft'" :disabled="!canTestDraft" @click="testDraft"><Wifi :size="15" />{{ t('models.testBeforeSave') }}</Button>
        <Button type="submit" :loading="saving" :disabled="!canSave">{{ t('common.save') }}</Button>
      </template>
    </ModalShell>
    <ModalShell v-model="showDelete" :title="t('models.deleteTitle')" max-width="max-w-lg">
      <div class="flex items-start gap-3 rounded-lg bg-red-50 p-4 text-sm text-red-700 dark:bg-red-950/30 dark:text-red-300"><CircleAlert class="mt-0.5 shrink-0" :size="18" /><div><p class="font-semibold">{{ t('models.confirmDelete', { name: pendingDelete?.name || '' }) }}</p><p class="mt-1 text-xs leading-5">{{ t('models.deleteWarning') }}</p></div></div>
      <template #footer><Button type="button" variant="secondary" @click="showDelete = false">{{ t('common.cancel') }}</Button><Button type="button" variant="danger" :loading="Boolean(deleting)" @click="confirmRemove"><Trash2 :size="15" />{{ t('common.delete') }}</Button></template>
    </ModalShell>
  </AppShell>
</template>
