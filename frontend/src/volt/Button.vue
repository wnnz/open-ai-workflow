<script setup lang="ts">
import Button from 'primevue/button'
withDefaults(defineProps<{
  label?: string
  icon?: string
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger' | 'link'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  disabled?: boolean
  active?: boolean
  block?: boolean
  type?: 'button' | 'submit' | 'reset'
}>(), { variant: 'primary', size: 'md', type: 'button' })
</script>

<template>
  <Button :label="label" :icon="icon" :loading="loading" :disabled="disabled" :type="type"
    class="focus-ring inline-flex items-center justify-center gap-2 rounded-lg font-medium transition-[background-color,border-color,color,filter,transform] duration-150 active:scale-[0.98] disabled:pointer-events-none disabled:opacity-50"
    :class="[
      size === 'sm' ? 'h-8 px-3 text-xs' : size === 'lg' ? 'h-10 px-4 text-sm' : 'h-9 px-3.5 text-sm',
      block && 'w-full',
      variant === 'primary' && 'bg-[var(--primary)] text-white hover:brightness-95',
      variant === 'secondary' && 'surface text-[var(--text)] hover:border-[color-mix(in_srgb,var(--primary),var(--border)_55%)] hover:bg-[var(--primary-soft)] hover:text-[var(--primary)] hover:brightness-95',
      variant === 'ghost' && 'text-[var(--muted)] hover:bg-[var(--panel-subtle)] hover:text-[var(--text)] hover:brightness-95',
      variant === 'danger' && 'bg-red-600 text-white hover:bg-red-700',
      variant === 'link' && 'h-auto px-0 text-[var(--primary)] hover:brightness-90 hover:underline',
      active && 'bg-[var(--primary-soft)] text-[var(--primary)]',
    ]">
    <slot />
  </Button>
</template>
