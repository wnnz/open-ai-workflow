<script setup lang="ts">
import { ShieldAlert } from 'lucide-vue-next'
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import FormField from '@/components/ui/FormField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import ToggleSwitch from '@/volt/ToggleSwitch.vue'
import BranchButton from './BranchButton.vue'
import JsonEditorField from './JsonEditorField.vue'
import NodeConfigSection from './NodeConfigSection.vue'

const props = defineProps<{ config: any }>()
const emit = defineEmits<{ 'connect-error': [] }>()
const { t } = useI18n()
const defaultOutputText = ref('{}')
const defaultOutputError = ref('')

props.config.retry = { enabled: false, max_retries: 3, interval_seconds: 0, ...(props.config.retry || {}) }
props.config.error_strategy ||= 'fail'
props.config.default_output ||= {}

watch(() => props.config.default_output, value => {
  if (!defaultOutputError.value) defaultOutputText.value = JSON.stringify(value || {}, null, 2)
}, { immediate: true, deep: true })

function updateDefaultOutput() {
  try {
    const parsed = JSON.parse(defaultOutputText.value || '{}')
    if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) throw new Error('object required')
    props.config.default_output = parsed
    defaultOutputError.value = ''
  } catch {
    defaultOutputError.value = t('designer.invalidJsonObject')
  }
}
</script>

<template>
  <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.executionPolicy')" :hint="t('designer.executionPolicyHint')" kind="policy" collapsible :default-expanded="false">
    <template #icon><ShieldAlert :size="14" /></template>
    <div class="space-y-3">
      <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
        <div class="flex items-start gap-3"><div class="min-w-0 flex-1"><h4 class="text-[11px] font-semibold">{{ t('designer.retryOnFailure') }}</h4><p class="muted mt-1 text-[10px] leading-4">{{ t('designer.retryOnFailureHint') }}</p></div><ToggleSwitch v-model="config.retry.enabled" :label="t('designer.retryOnFailure')" /></div>
        <div v-if="config.retry.enabled" class="mt-3 grid grid-cols-2 gap-2 border-t border-[var(--border)] pt-3">
          <FormField :label="t('designer.maxRetries')" compact><InputText v-model.number="config.retry.max_retries" type="number" min="1" max="10" /></FormField>
          <FormField :label="t('designer.retryInterval')" compact><InputText v-model.number="config.retry.interval_seconds" type="number" min="0" max="30" step="0.5" /></FormField>
        </div>
        <p v-else class="muted mt-2 text-[10px] leading-4">{{ t('designer.retryDisabledHint') }}</p>
      </section>

      <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
        <h4 class="text-[11px] font-semibold">{{ t('designer.errorHandling') }}</h4><p class="muted mt-1 text-[10px] leading-4">{{ t('designer.errorHandlingHint') }}</p>
        <FormField class="mt-3" :label="t('designer.errorStrategy')" compact>
          <Select v-model="config.error_strategy" class="!h-9 !text-xs">
            <option value="fail">{{ t('designer.errorStrategies.fail') }}</option>
            <option value="default_value">{{ t('designer.errorStrategies.default_value') }}</option>
            <option value="error_branch">{{ t('designer.errorStrategies.error_branch') }}</option>
          </Select>
        </FormField>
        <JsonEditorField v-if="config.error_strategy === 'default_value'" v-model="defaultOutputText" class="mt-3" :label="t('designer.defaultOutput')" :error="defaultOutputError" height-class="h-28" @input="updateDefaultOutput" />
        <div v-else-if="config.error_strategy === 'error_branch'" class="mt-3">
          <p class="muted mb-2 text-[11px] leading-4">{{ t('designer.errorBranchHint') }}</p>
          <BranchButton :label="t('designer.connectErrorBranch')" tone="warning" @click="emit('connect-error')" />
        </div>
      </section>
    </div>
  </NodeConfigSection>
</template>
