<script setup lang="ts">
defineOptions({ inheritAttrs: false })
defineProps<{ modelValue?: string | number | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: string]; change: [event: Event] }>()
function change(event: Event) {
  emit('update:modelValue', (event.target as HTMLSelectElement).value)
  emit('change', event)
}
</script>

<template>
  <select
    v-bind="$attrs"
    :value="modelValue ?? ''"
    class="focus-ring h-10 w-full rounded-lg border border-[var(--border)] bg-[var(--panel)] px-3 text-sm text-[var(--text)]"
    @change="change"
  ><slot /></select>
</template>
