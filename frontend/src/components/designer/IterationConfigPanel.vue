<script setup lang="ts">
import VariableField from '@/components/VariableField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'

defineProps<{ config: Record<string, any>; variableGroups: any[] }>()
</script>

<template>
  <section class="mt-5 space-y-4">
    <label class="field-label">{{ $t('designer.iterationSource') }}<VariableField v-model="config.source" class="mt-1.5 font-mono" :groups="variableGroups" placeholder="{{node.items}}" /></label>
    <label class="field-label">{{ $t('designer.itemVariable') }}<InputText v-model="config.item_variable" class="mt-1.5 font-mono" placeholder="item" /></label>
    <label class="field-label">{{ $t('designer.iterationOutput') }}<VariableField v-model="config.output" class="mt-1.5 font-mono" :groups="variableGroups" :placeholder="$t('designer.iterationOutputPlaceholder')" /></label>
    <label class="field-label">{{ $t('designer.iterationMode') }}<Select v-model="config.mode" class="mt-1.5 !h-9 !text-xs"><option value="sequential">{{ $t('designer.sequential') }}</option><option value="parallel">{{ $t('designer.parallel') }}</option></Select></label>
    <label v-if="config.mode === 'parallel'" class="field-label">{{ $t('designer.concurrency') }}<InputText v-model.number="config.concurrency" class="mt-1.5" type="number" min="1" max="20" /></label>
    <div class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3 text-[11px] leading-5 text-[var(--muted)]">{{ $t('designer.iterationBodyHint') }}</div>
  </section>
</template>
