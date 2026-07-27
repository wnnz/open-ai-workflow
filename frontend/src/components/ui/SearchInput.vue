<script setup lang="ts">
import { Search } from 'lucide-vue-next'
import InputText from '@/volt/InputText.vue'
defineProps<{ modelValue: string; placeholder?: string }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <div class="relative"><Search class="muted pointer-events-none absolute left-3 top-1/2 -translate-y-1/2" :size="16" /><InputText :model-value="modelValue" class="!h-9 !border-0 !bg-[var(--panel-subtle)] !pl-9" :placeholder="placeholder" @update:model-value="$emit('update:modelValue', $event)" /></div>
</template>
