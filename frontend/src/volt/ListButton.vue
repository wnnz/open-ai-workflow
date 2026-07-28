<script setup lang="ts">
withDefaults(defineProps<{
  active?: boolean
  tone?: 'default' | 'danger' | 'primary'
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}>(), { tone: 'default', type: 'button' })
</script>

<template>
  <button :type="type" :disabled="disabled"
    class="focus-ring flex w-full items-center rounded-lg px-3 py-2 text-left text-sm transition-[background-color,color,filter] duration-150 hover:brightness-95 active:bg-[var(--panel-subtle)] disabled:pointer-events-none disabled:opacity-50"
    :class="[
      active ? 'bg-[var(--primary-soft)] text-[var(--primary)]' : 'hover:bg-[var(--panel-subtle)]',
      tone === 'danger' && 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30',
      tone === 'primary' && 'text-[var(--primary)]',
    ]"
  ><slot /></button>
</template>
