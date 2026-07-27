<script setup lang="ts">
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
  <div class="mt-5 space-y-4 border-t border-[var(--border)] pt-5">
    <NodeConfigSection :title="t('designer.retryOnFailure')" :hint="t('designer.retryOnFailureHint')" collapsible :default-expanded="config.retry.enabled">
      <template #actions><ToggleSwitch v-model="config.retry.enabled" :label="t('designer.retryOnFailure')" /></template>
      <div v-if="config.retry.enabled" class="grid grid-cols-2 gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
        <FormField :label="t('designer.maxRetries')" compact><InputText v-model.number="config.retry.max_retries" type="number" min="1" max="10" /></FormField>
        <FormField :label="t('designer.retryInterval')" compact><InputText v-model.number="config.retry.interval_seconds" type="number" min="0" max="30" step="0.5" /></FormField>
      </div>
      <p v-else class="muted rounded-lg bg-[var(--panel-subtle)] p-3 text-[11px]">{{ t('designer.retryDisabledHint') }}</p>
    </NodeConfigSection>

    <NodeConfigSection class="border-t border-[var(--border)] pt-4" :title="t('designer.errorHandling')" :hint="t('designer.errorHandlingHint')" collapsible :default-expanded="config.error_strategy !== 'fail'">
      <FormField :label="t('designer.errorStrategy')" compact>
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
    </NodeConfigSection>
  </div>
</template>
