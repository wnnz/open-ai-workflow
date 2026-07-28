<script setup lang="ts">
import { LoaderCircle } from 'lucide-vue-next'

withDefaults(defineProps<{
  label: string
  tone?: 'default' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  surface?: boolean
  active?: boolean
  loading?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}>(), { tone: 'default', size: 'md', type: 'button' })
</script>

<template>
  <button
    :type="type"
    :aria-label="label"
    :title="label"
    :disabled="disabled || loading"
    :aria-busy="loading || undefined"
    class="focus-ring inline-flex shrink-0 items-center justify-center rounded-lg transition-[background-color,border-color,color,filter,transform] duration-150 hover:brightness-95 active:scale-95 disabled:pointer-events-none disabled:opacity-40"
    :class="[
      size === 'sm' ? 'h-7 w-7' : size === 'lg' ? 'h-9 w-9' : 'h-8 w-8',
      surface && 'surface hover:border-[color-mix(in_srgb,var(--primary),var(--border)_55%)]',
      active && 'bg-[var(--primary-soft)] text-[var(--primary)]',
      tone === 'danger' ? 'text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30' : 'text-[var(--muted)] hover:bg-[var(--panel-subtle)] hover:text-[var(--text)]',
    ]"
  ><LoaderCircle v-if="loading" :size="14" class="animate-spin" /><slot v-else /></button>
</template>
