<script setup lang="ts">
import { Bot, CheckCircle2, Clock3, KeyRound, Pencil, Trash2, Wifi } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import Button from '@/volt/Button.vue'
import IconButton from '@/volt/IconButton.vue'

export type ProviderStatus = 'untested' | 'connected' | 'warning' | 'failed'
export type ModelProviderSummary = {
  id: string; name: string; base_url: string; default_model: string; has_api_key: boolean
  last_tested_at?: string | null; last_test_status: ProviderStatus; last_test_latency_ms?: number | null
}

defineProps<{ provider: ModelProviderSummary; canManage: boolean; testing?: boolean; deleting?: boolean }>()
const emit = defineEmits<{ test: []; fullTest: []; edit: []; remove: [] }>()
const { t } = useI18n()

function statusClass(status: ProviderStatus) {
  if (status === 'connected') return 'text-emerald-700 bg-emerald-50 dark:text-emerald-300 dark:bg-emerald-950/30'
  if (status === 'warning') return 'text-amber-700 bg-amber-50 dark:text-amber-300 dark:bg-amber-950/30'
  if (status === 'failed') return 'text-red-700 bg-red-50 dark:text-red-300 dark:bg-red-950/30'
  return 'text-[var(--muted)] bg-[var(--panel-subtle)]'
}
</script>

<template>
  <article class="surface flex min-h-56 flex-col rounded-xl p-4">
    <div class="flex items-start gap-3">
      <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><Bot :size="20" /></span>
      <div class="min-w-0 flex-1"><h3 class="truncate font-semibold">{{ provider.name }}</h3><p class="muted mt-1 truncate text-xs" :title="provider.base_url">{{ provider.base_url }}</p></div>
      <span class="rounded-full px-2 py-1 text-[10px] font-medium" :class="statusClass(provider.last_test_status)">{{ t(`models.statuses.${provider.last_test_status}`) }}</span>
    </div>
    <dl class="mt-4 grid grid-cols-2 gap-2 rounded-lg bg-[var(--panel-subtle)] p-3 text-xs">
      <div class="col-span-2"><dt class="muted">{{ t('models.defaultModel') }}</dt><dd class="mt-1 truncate font-medium" :title="provider.default_model">{{ provider.default_model }}</dd></div>
      <div><dt class="muted flex items-center gap-1"><KeyRound :size="12" />API Key</dt><dd class="mt-1">{{ provider.has_api_key ? t('models.configuredKey') : t('models.noKey') }}</dd></div>
      <div><dt class="muted flex items-center gap-1"><Clock3 :size="12" />{{ t('models.latency') }}</dt><dd class="mt-1">{{ provider.last_test_latency_ms == null ? '—' : `${provider.last_test_latency_ms} ms` }}</dd></div>
    </dl>
    <p v-if="provider.last_tested_at" class="muted mt-2 text-[10px]">{{ t('models.lastTested') }} {{ new Date(provider.last_tested_at).toLocaleString() }}</p>
    <div v-if="canManage" class="mt-auto flex items-center justify-end gap-1 pt-4">
      <Button variant="secondary" :loading="testing" @click="emit('test')"><Wifi :size="14" />{{ t('models.test') }}</Button>
      <IconButton :label="t('models.fullTest')" @click="emit('fullTest')"><CheckCircle2 :size="15" /></IconButton>
      <IconButton :label="t('common.edit')" @click="emit('edit')"><Pencil :size="15" /></IconButton>
      <IconButton :label="t('common.delete')" tone="danger" :disabled="deleting" @click="emit('remove')"><Trash2 :size="15" /></IconButton>
    </div>
  </article>
</template>
