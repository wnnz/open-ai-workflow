<script setup lang="ts">
withDefaults(defineProps<{ label: string; hint?: string; error?: string; required?: boolean; forId?: string; compact?: boolean }>(), { hint: '', error: '', required: false, forId: undefined, compact: false })
</script>

<template>
  <label class="block" :class="compact ? 'text-xs font-semibold' : 'text-sm font-medium'" :for="forId">
    <span>{{ label }}<span v-if="required" class="ml-1 text-red-500">*</span></span>
    <span v-if="hint" class="muted mt-1 block text-xs font-normal leading-5">{{ hint }}</span>
    <span class="mt-1.5 block"><slot /></span>
    <span v-if="error" class="mt-1.5 block text-xs font-normal text-red-600">{{ error }}</span>
  </label>
</template>
