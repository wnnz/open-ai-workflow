<script setup lang="ts">
import InputText from 'primevue/inputtext'
defineOptions({ inheritAttrs: false })
defineProps<{ modelValue?: string; placeholder?: string; type?: string; required?: boolean }>()
defineEmits<{ 'update:modelValue': [value: string] }>()
</script>

<template>
  <InputText v-bind="$attrs" :model-value="modelValue" :placeholder="placeholder" :type="type" :required="required"
    class="focus-ring h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--panel)] px-3 text-sm text-[var(--text)] placeholder:text-[var(--muted)]"
    @update:model-value="$emit('update:modelValue', $event ?? '')" />
</template>
