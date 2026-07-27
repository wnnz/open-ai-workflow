<script setup lang="ts">
withDefaults(defineProps<{ title: string; description?: string; compact?: boolean }>(), { description: '', compact: false })
</script>

<template>
  <div class="muted flex flex-col items-center justify-center text-center" :class="compact ? 'px-4 py-10' : 'px-6 py-20'">
    <div v-if="$slots.icon" class="mb-3 opacity-40"><slot name="icon" /></div><p class="text-sm font-medium text-[var(--text)]">{{ title }}</p><p v-if="description" class="mt-1 max-w-md text-xs leading-5">{{ description }}</p><div v-if="$slots.actions" class="mt-4"><slot name="actions" /></div>
  </div>
</template>
