<script setup lang="ts">
withDefaults(defineProps<{ modelValue?: boolean; label?: string; disabled?: boolean }>(), { modelValue: false, label: '', disabled: false })
const emit = defineEmits<{ 'update:modelValue': [value: boolean] }>()
</script>

<template>
  <button
    type="button"
    role="switch"
    :aria-checked="modelValue"
    :aria-label="label"
    :disabled="disabled"
    class="relative h-5 w-9 shrink-0 rounded-full transition-colors disabled:cursor-not-allowed disabled:opacity-50"
    :class="modelValue ? 'bg-[var(--primary)]' : 'bg-slate-300 dark:bg-slate-600'"
    @click="emit('update:modelValue', !modelValue)"
  >
    <span class="absolute top-0.5 h-4 w-4 rounded-full bg-white shadow-sm transition-transform" :class="modelValue ? 'translate-x-[18px]' : 'translate-x-0.5'"></span>
  </button>
</template>
