<script setup lang="ts">
defineOptions({ inheritAttrs: false })
defineProps<{ modelValue?: string | number | null }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <textarea
    v-bind="$attrs"
    :value="modelValue ?? ''"
    class="app-textarea focus-ring w-full resize-y border border-[var(--border)] bg-[var(--input-bg)] px-3 py-2 text-[var(--text)] placeholder:text-[var(--muted)] read-only:bg-[var(--panel-subtle)] disabled:cursor-not-allowed disabled:bg-[var(--panel-subtle)] disabled:text-[var(--muted)] disabled:opacity-100"
    @input="$emit('update:modelValue', ($event.target as HTMLTextAreaElement).value)"
  ></textarea>
</template>

<style scoped>
.app-textarea { border-radius: var(--control-radius, 0.5rem); font-size: var(--control-font-size, 0.875rem); }
</style>
