<script setup lang="ts">
withDefaults(defineProps<{ label: string; tone?: 'default' | 'danger'; size?: 'sm' | 'md'; type?: 'button' | 'submit' }>(), { tone: 'default', size: 'md', type: 'button' })
</script>

<template>
  <button
    :type="type"
    :aria-label="label"
    :title="label"
    class="focus-ring inline-flex shrink-0 items-center justify-center rounded-lg transition-colors disabled:cursor-not-allowed disabled:opacity-40"
    :class="[
      size === 'sm' ? 'h-7 w-7' : 'h-8 w-8',
      tone === 'danger' ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30' : 'text-[var(--muted)] hover:bg-[var(--panel-subtle)] hover:text-[var(--text)]',
    ]"
  ><slot /></button>
</template>
