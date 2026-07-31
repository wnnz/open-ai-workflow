<script setup lang="ts">
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

defineProps<{ config: Record<string, any>; variableGroups: any[] }>()
</script>

<template>
  <section class="mt-5">
    <NodeConfigSection :title="$t('designer.nodeParameters')" :hint="$t('designer.nodeParametersHint')" kind="parameters">
      <div class="space-y-4"><FormField :label="$t('designer.itemVariable')" compact><InputText v-model="config.item_variable" class="font-mono" placeholder="item" /></FormField><FormField :label="$t('designer.iterationMode')" compact><Select v-model="config.mode"><option value="sequential">{{ $t('designer.sequential') }}</option><option value="parallel">{{ $t('designer.parallel') }}</option></Select></FormField><FormField v-if="config.mode === 'parallel'" :label="$t('designer.concurrency')" compact><InputText v-model.number="config.concurrency" type="number" min="1" max="20" /></FormField><NodeSettingCard><p class="text-[11px] leading-5 text-[var(--muted)]">{{ $t('designer.iterationBodyHint') }}</p></NodeSettingCard></div>
    </NodeConfigSection>
    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="$t('designer.inputVariables')" :hint="$t('designer.inputVariablesHint')" :count="2" kind="input" collapsible><div class="space-y-3"><NodeSettingCard :title="$t('designer.iterationSource')" type="Array" required><VariableField v-model="config.source" class="font-mono" :groups="variableGroups" :placeholder="$t('designer.variableReferencePlaceholder')" /></NodeSettingCard><NodeSettingCard :title="$t('designer.iterationOutput')" type="Any"><VariableField v-model="config.output" class="font-mono" :groups="variableGroups" :placeholder="$t('designer.iterationOutputPlaceholder')" /></NodeSettingCard></div></NodeConfigSection>
  </section>
</template>
