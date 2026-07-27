<script setup lang="ts">
import Select from '@/volt/Select.vue'

defineProps<{ config: Record<string, any> }>()
</script>

<template>
  <section class="mt-5 space-y-4">
    <label class="field-label">
      {{ $t('designer.waitMode') }}
      <Select v-model="config.mode" class="mt-1.5 !h-9 !text-xs">
        <option value="all">{{ $t('designer.waitModeAll') }}</option>
        <option value="any">{{ $t('designer.waitModeAny') }}</option>
      </Select>
    </label>
    <div class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3 text-[11px] leading-5 text-[var(--muted)]">
      {{ config.mode === 'any' ? $t('designer.waitAnyHint') : $t('designer.waitAllHint') }}
    </div>
  </section>
</template>
