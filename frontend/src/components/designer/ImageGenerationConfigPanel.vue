<script setup lang="ts">
import { computed, watch } from 'vue'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'

const props = defineProps<{
  config: any
  providers: any[]
  variableGroups: WorkflowVariableGroup[]
}>()
props.config.timeout_seconds ??= 600

const selectedProvider = computed(() => props.providers.find(provider => provider.id === props.config.provider_id))
const pngOutput = computed(() => props.config.output_format === 'png')
const modelOptions = computed(() => {
  const provider = selectedProvider.value
  const models = Array.isArray(provider?.available_models) ? provider.available_models : []
  const imageModels = models.filter((model: string) => /image/i.test(model))
  return imageModels.length ? imageModels : models
})

watch(() => props.config.output_format, (format) => {
  if (format === 'png') props.config.output_compression = 100
}, { immediate: true })

function selectProvider() {
  const provider = selectedProvider.value
  if (!provider) return
  props.config.provider_name = provider.name
  props.config.model = modelOptions.value.find((model: string) => /image/i.test(model)) || provider.default_model
}
</script>

<template>
  <section class="mt-5 space-y-5">
    <div class="space-y-3">
      <label class="field-label">{{ $t('designer.modelProvider') }} <span class="text-red-500">*</span>
        <Select v-model="config.provider_id" class="mt-1.5 !h-9 !text-xs" @change="selectProvider">
          <option value="">{{ $t('designer.selectModelProvider') }}</option>
          <option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option>
        </Select>
      </label>
      <label class="field-label">{{ $t('designer.modelName') }} <span class="text-red-500">*</span>
        <Select v-model="config.model" class="mt-1.5 !h-9 !text-xs" editable allow-custom-value :filter-options="false" highlight-matches>
          <option v-for="model in modelOptions" :key="model" :value="model">{{ model }}</option>
        </Select>
      </label>
      <p v-if="!providers.length" class="resource-empty">{{ $t('designer.noModels') }}</p>
    </div>

    <label class="field-label">{{ $t('designer.imagePrompt') }} <span class="text-red-500">*</span>
      <VariableField v-model="config.prompt" class="mt-1.5" :groups="variableGroups" multiline :rows="6" :placeholder="$t('designer.imagePromptPlaceholder')" />
    </label>

    <div class="grid grid-cols-2 gap-3">
      <label class="field-label">{{ $t('designer.imageSize') }}
        <VariableField v-model="config.size" class="mt-1.5 font-mono" :groups="variableGroups" placeholder="{{inputs.resolution}}" />
      </label>
      <label class="field-label">{{ $t('designer.imageCount') }}
        <VariableField v-model="config.count" class="mt-1.5 font-mono" :groups="variableGroups" placeholder="{{inputs.count}}" />
      </label>
    </div>

    <details class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)]" open>
      <summary class="cursor-pointer px-3 py-2.5 text-xs font-semibold">{{ $t('designer.imageOutputSettings') }}</summary>
      <div class="grid grid-cols-2 gap-3 border-t border-[var(--border)] p-3">
        <label class="field-label">{{ $t('designer.imageQuality') }}<Select v-model="config.quality" class="mt-1.5 !h-9 !text-xs"><option v-for="value in ['auto','low','medium','high']" :key="value" :value="value">{{ value }}</option></Select></label>
        <label class="field-label">{{ $t('designer.imageFormat') }}<Select v-model="config.output_format" class="mt-1.5 !h-9 !text-xs"><option v-for="value in ['webp','png','jpeg']" :key="value" :value="value">{{ value }}</option></Select></label>
        <label class="field-label">{{ $t('designer.imageCompression') }}<InputText v-model.number="config.output_compression" class="mt-1.5" type="number" min="0" max="100" :disabled="pngOutput" /></label>
        <label class="field-label">{{ $t('designer.imageBackground') }}<Select v-model="config.background" class="mt-1.5 !h-9 !text-xs"><option v-for="value in ['auto','opaque','transparent']" :key="value" :value="value">{{ value }}</option></Select></label>
        <label class="field-label col-span-2">{{ $t('designer.imageTimeout') }}<InputText v-model.number="config.timeout_seconds" class="mt-1.5" type="number" min="30" max="900" /></label>
      </div>
    </details>
  </section>
</template>
