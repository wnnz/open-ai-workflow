<script setup lang="ts">
import VariableField from '@/components/VariableField.vue'
import InputText from '@/volt/InputText.vue'

defineProps<{ config: Record<string, any>; variableGroups: any[] }>()
</script>

<template>
  <section class="mt-5 space-y-4">
    <label class="field-label">{{ $t('designer.loopCondition') }}<VariableField v-model="config.condition" class="mt-1.5 font-mono" :groups="variableGroups" multiline :rows="5" :placeholder="$t('designer.loopConditionPlaceholder')" /></label>
    <label class="field-label">{{ $t('designer.maxIterations') }}<InputText v-model.number="config.max_iterations" class="mt-1.5" type="number" min="1" max="100" /></label>
    <label class="field-label">{{ $t('designer.loopOutput') }}<VariableField v-model="config.output" class="mt-1.5 font-mono" :groups="variableGroups" :placeholder="$t('designer.loopOutputPlaceholder')" /></label>
    <div class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3 text-[11px] leading-5 text-[var(--muted)]">{{ $t('designer.loopBodyHint') }}</div>
  </section>
</template>
