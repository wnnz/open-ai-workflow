<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'
import JsonEditorField from './JsonEditorField.vue'
import NodeConfigSection from './NodeConfigSection.vue'

type HttpBuffers = { httpHeaders: string; httpQuery: string; httpBody: string }

const props = defineProps<{
  config: any
  variableGroups: WorkflowVariableGroup[]
  buffers: HttpBuffers
  errors: Record<string, string>
}>()
const emit = defineEmits<{ structured: [field: string, buffer: keyof HttpBuffers] }>()
const { t } = useI18n()

props.config.auth ||= { type: 'none', token: '', username: '', password: '', key: '', value: '', location: 'header' }
props.config.query ||= {}
props.config.headers ||= {}
props.config.body_type ||= props.config.body == null ? 'none' : 'json'
props.config.max_response_bytes ||= 2_000_000
props.config.follow_redirects ??= false

function changeBodyType(event: Event) {
  const type = (event.target as HTMLSelectElement).value
  props.config.body_type = type
  props.config.body = type === 'raw' ? '' : type === 'none' ? null : {}
  props.buffers.httpBody = type === 'none' ? '' : type === 'raw' ? '' : '{}'
}
</script>

<template>
  <div class="mt-5 space-y-4">
    <div class="grid grid-cols-[110px_minmax(0,1fr)] gap-2">
      <FormField :label="t('designer.method')" compact>
        <Select v-model="config.method" class="!h-9 !text-xs">
          <option v-for="method in ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS']" :key="method" :value="method">{{ method }}</option>
        </Select>
      </FormField>
      <FormField label="URL" compact>
        <VariableField v-model="config.url" :groups="variableGroups" placeholder="https://api.example.com" />
      </FormField>
    </div>

    <NodeConfigSection :title="t('designer.authentication')" :hint="t('designer.httpAuthHint')">
      <FormField :label="t('designer.authType')" compact>
        <Select v-model="config.auth.type" class="!h-9 !text-xs">
          <option v-for="type in ['none', 'bearer', 'basic', 'api_key']" :key="type" :value="type">{{ t(`designer.authTypes.${type}`) }}</option>
        </Select>
      </FormField>
      <FormField v-if="config.auth.type === 'bearer'" class="mt-3" :label="t('designer.bearerToken')" compact>
        <VariableField v-model="config.auth.token" class="font-mono" :groups="variableGroups" placeholder="{{inputs.token}}" />
      </FormField>
      <div v-else-if="config.auth.type === 'basic'" class="mt-3 grid grid-cols-2 gap-2">
        <FormField :label="t('designer.username')" compact><VariableField v-model="config.auth.username" :groups="variableGroups" /></FormField>
        <FormField :label="t('designer.password')" compact><VariableField v-model="config.auth.password" :groups="variableGroups" /></FormField>
      </div>
      <div v-else-if="config.auth.type === 'api_key'" class="mt-3 grid grid-cols-2 gap-2">
        <FormField :label="t('designer.apiKeyName')" compact><InputText v-model="config.auth.key" class="!h-9 font-mono" placeholder="X-API-Key" /></FormField>
        <FormField :label="t('designer.apiKeyLocation')" compact><Select v-model="config.auth.location" class="!h-9 !text-xs"><option value="header">Header</option><option value="query">Query</option></Select></FormField>
        <FormField class="col-span-2" :label="t('designer.apiKeyValue')" compact><VariableField v-model="config.auth.value" class="font-mono" :groups="variableGroups" placeholder="{{inputs.api_key}}" /></FormField>
      </div>
    </NodeConfigSection>

    <JsonEditorField v-model="buffers.httpQuery" :label="t('designer.queryParameters')" :error="errors.httpQuery" height-class="h-24" @input="emit('structured', 'query', 'httpQuery')" />
    <JsonEditorField v-model="buffers.httpHeaders" :label="t('designer.requestHeaders')" :error="errors.httpHeaders" height-class="h-28" @input="emit('structured', 'headers', 'httpHeaders')" />

    <NodeConfigSection :title="t('designer.requestBody')">
      <FormField :label="t('designer.bodyType')" compact>
        <Select :model-value="config.body_type" class="!h-9 !text-xs" @change="changeBodyType">
          <option v-for="type in ['none', 'json', 'raw', 'form']" :key="type" :value="type">{{ t(`designer.bodyTypes.${type}`) }}</option>
        </Select>
      </FormField>
      <Textarea v-if="config.body_type === 'raw'" v-model="config.body" class="mt-3 h-32 font-mono !text-xs" :placeholder="t('designer.rawBodyPlaceholder')" />
      <JsonEditorField v-else-if="config.body_type !== 'none'" v-model="buffers.httpBody" class="mt-3" :label="config.body_type === 'form' ? t('designer.formBody') : 'JSON'" :error="errors.httpBody" height-class="h-32" @input="emit('structured', 'body', 'httpBody')" />
    </NodeConfigSection>

    <div class="grid grid-cols-2 gap-2">
      <FormField :label="t('designer.timeoutSeconds')" compact><InputText v-model.number="config.timeout_seconds" type="number" min="1" max="300" /></FormField>
      <FormField :label="t('designer.maxResponseBytes')" compact><InputText v-model.number="config.max_response_bytes" type="number" min="1024" max="10000000" step="1024" /></FormField>
    </div>
    <label class="flex cursor-pointer items-center gap-2 rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] px-3 py-2.5 text-xs font-medium">
      <input v-model="config.follow_redirects" class="accent-[var(--primary)]" type="checkbox">
      {{ t('designer.followRedirects') }}
    </label>
  </div>
</template>
