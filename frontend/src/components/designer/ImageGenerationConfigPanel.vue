<script setup lang="ts">
import { computed, watch } from 'vue'
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

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
  <section class="mt-5">
    <NodeConfigSection :title="$t('designer.nodeParameters')" :hint="$t('designer.nodeParametersHint')" kind="parameters">
      <div class="space-y-4">
        <FormField :label="$t('designer.modelProvider')" required compact>
          <Select v-model="config.provider_id" @change="selectProvider">
          <option value="">{{ $t('designer.selectModelProvider') }}</option>
          <option v-for="provider in providers" :key="provider.id" :value="provider.id">{{ provider.name }}</option>
          </Select>
        </FormField>
        <FormField :label="$t('designer.modelName')" required compact>
          <Select v-model="config.model" editable allow-custom-value :filter-options="false" highlight-matches>
          <option v-for="model in modelOptions" :key="model" :value="model">{{ model }}</option>
          </Select>
        </FormField>
        <p v-if="!providers.length" class="resource-empty">{{ $t('designer.noModels') }}</p>

        <NodeConfigSection class="border-t border-[var(--border)] pt-4" :title="$t('designer.imageOutputSettings')" collapsible :default-expanded="false">
          <div class="grid grid-cols-2 gap-3">
            <FormField :label="$t('designer.imageQuality')" compact><Select v-model="config.quality"><option v-for="value in ['auto','low','medium','high']" :key="value" :value="value">{{ value }}</option></Select></FormField>
            <FormField :label="$t('designer.imageFormat')" compact><Select v-model="config.output_format"><option v-for="value in ['webp','png','jpeg']" :key="value" :value="value">{{ value }}</option></Select></FormField>
            <FormField :label="$t('designer.imageCompression')" compact><InputText v-model.number="config.output_compression" type="number" min="0" max="100" :disabled="pngOutput" /></FormField>
            <FormField :label="$t('designer.imageBackground')" compact><Select v-model="config.background"><option v-for="value in ['auto','opaque','transparent']" :key="value" :value="value">{{ value }}</option></Select></FormField>
            <FormField class="col-span-2" :label="$t('designer.imageTimeout')" compact><InputText v-model.number="config.timeout_seconds" type="number" min="30" max="900" /></FormField>
          </div>
        </NodeConfigSection>
      </div>
    </NodeConfigSection>

    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="$t('designer.inputVariables')" :hint="$t('designer.inputVariablesHint')" :count="'size' in config ? 3 : 2" kind="input" collapsible>
      <div class="space-y-3">
        <NodeSettingCard :title="$t('designer.imagePrompt')" type="String" required><VariableField v-model="config.prompt" :groups="variableGroups" multiline :rows="6" :placeholder="$t('designer.imagePromptPlaceholder')" /></NodeSettingCard>
        <div class="grid grid-cols-2 gap-3">
          <NodeSettingCard v-if="'size' in config" :title="$t('designer.imageSize')" type="String"><VariableField v-model="config.size" class="font-mono" :groups="variableGroups" placeholder="{{inputs.resolution}}" /></NodeSettingCard>
          <NodeSettingCard :title="$t('designer.imageCount')" type="Number" :class="{ 'col-span-2': !('size' in config) }"><VariableField v-model="config.count" class="font-mono" :groups="variableGroups" placeholder="{{inputs.count}}" /></NodeSettingCard>
        </div>
      </div>
    </NodeConfigSection>
  </section>
</template>
