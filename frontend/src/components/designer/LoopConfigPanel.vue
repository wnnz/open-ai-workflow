<script setup lang="ts">
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import InputText from '@/volt/InputText.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

defineProps<{ config: Record<string, any>; variableGroups: any[] }>()
</script>

<template>
  <section class="mt-5">
    <NodeConfigSection :title="$t('designer.nodeParameters')" :hint="$t('designer.nodeParametersHint')" kind="parameters"><div class="space-y-4"><FormField :label="$t('designer.maxIterations')" compact><InputText v-model.number="config.max_iterations" type="number" min="1" max="100" /></FormField><NodeSettingCard><p class="text-[11px] leading-5 text-[var(--muted)]">{{ $t('designer.loopBodyHint') }}</p></NodeSettingCard></div></NodeConfigSection>
    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="$t('designer.inputVariables')" :hint="$t('designer.inputVariablesHint')" :count="2" kind="input" collapsible><div class="space-y-3"><NodeSettingCard :title="$t('designer.loopCondition')" type="Boolean" required><VariableField v-model="config.condition" class="font-mono" :groups="variableGroups" multiline :rows="5" :placeholder="$t('designer.loopConditionPlaceholder')" /></NodeSettingCard><NodeSettingCard :title="$t('designer.loopOutput')" type="Any"><VariableField v-model="config.output" class="font-mono" :groups="variableGroups" :placeholder="$t('designer.loopOutputPlaceholder')" /></NodeSettingCard></div></NodeConfigSection>
  </section>
</template>
