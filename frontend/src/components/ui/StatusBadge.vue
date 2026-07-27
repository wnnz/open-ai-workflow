<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: 'neutral' | 'success' | 'warning' | 'danger' | 'info' }>(), { tone: 'neutral' })
</script>

<template>
  <span class="inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium" :class="{
    'bg-[var(--panel-subtle)] text-[var(--muted)]': tone === 'neutral',
    'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300': tone === 'success',
    'bg-amber-50 text-amber-700 dark:bg-amber-950/30 dark:text-amber-300': tone === 'warning',
    'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300': tone === 'danger',
    'bg-[var(--primary-soft)] text-[var(--primary)]': tone === 'info',
  }">{{ label }}</span>
</template>
