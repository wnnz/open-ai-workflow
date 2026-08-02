<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <header class="flex shrink-0 flex-col gap-4 sm:flex-row sm:items-start sm:justify-between sm:gap-5">
    <div class="min-w-0"><h1 class="text-xl font-semibold">{{ title }}</h1><p v-if="subtitle" class="muted mt-1 text-sm">{{ subtitle }}</p></div>
    <div v-if="$slots.actions" class="flex flex-wrap items-center gap-2 sm:shrink-0"><slot name="actions" /></div>
  </header>
</template>
