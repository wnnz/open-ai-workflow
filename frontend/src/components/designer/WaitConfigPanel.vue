<script setup lang="ts">
import Select from '@/volt/Select.vue'
import FormField from '@/components/ui/FormField.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

defineProps<{ config: Record<string, any> }>()
</script>

<template>
  <section class="mt-5">
    <NodeConfigSection :title="$t('designer.nodeParameters')" :hint="$t('designer.nodeParametersHint')" kind="parameters">
      <div class="space-y-4">
        <FormField :label="$t('designer.waitMode')" compact><Select v-model="config.mode">
        <option value="all">{{ $t('designer.waitModeAll') }}</option>
        <option value="any">{{ $t('designer.waitModeAny') }}</option>
        </Select></FormField>
        <NodeSettingCard><p class="text-[11px] leading-5 text-[var(--muted)]">{{ config.mode === 'any' ? $t('designer.waitAnyHint') : $t('designer.waitAllHint') }}</p></NodeSettingCard>
      </div>
    </NodeConfigSection>
  </section>
</template>
