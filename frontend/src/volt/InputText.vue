<script setup lang="ts">
import InputText from 'primevue/inputtext'
defineOptions({ inheritAttrs: false })
defineProps<{ modelValue?: string; placeholder?: string; type?: string; required?: boolean }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <InputText v-bind="$attrs" :model-value="modelValue" :placeholder="placeholder" :type="type" :required="required"
    class="app-input focus-ring w-full border border-[var(--border)] bg-[var(--input-bg)] px-3 text-[var(--text)] placeholder:text-[var(--muted)] read-only:bg-[var(--panel-subtle)] disabled:cursor-not-allowed disabled:bg-[var(--panel-subtle)] disabled:text-[var(--muted)] disabled:opacity-100"
    @update:model-value="$emit('update:modelValue', $event ?? '')" />
</template>

<style scoped>
.app-input { height: var(--control-height, 2.5rem); border-radius: var(--control-radius, 0.5rem); font-size: var(--control-font-size, 0.875rem); }
</style>
