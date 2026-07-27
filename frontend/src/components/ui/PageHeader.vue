<script setup lang="ts">
defineProps<{ title: string; subtitle?: string }>()
</script>

<template>
  <header class="flex shrink-0 items-start justify-between gap-5">
    <div class="min-w-0"><h1 class="text-xl font-semibold">{{ title }}</h1><p v-if="subtitle" class="muted mt-1 text-sm">{{ subtitle }}</p></div>
    <div v-if="$slots.actions" class="flex shrink-0 items-center gap-2"><slot name="actions" /></div>
  </header>
</template>
