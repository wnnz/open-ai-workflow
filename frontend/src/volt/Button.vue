<script setup lang="ts">
import Button from 'primevue/button'
withDefaults(defineProps<{ label?: string; icon?: string; variant?: 'primary' | 'secondary' | 'ghost' | 'danger'; loading?: boolean; disabled?: boolean; type?: 'button' | 'submit' }>(), { variant: 'primary', type: 'button' })
</script>

<template>
  <Button :label="label" :icon="icon" :loading="loading" :disabled="disabled" :type="type"
    class="focus-ring inline-flex h-9 items-center justify-center gap-2 rounded-lg px-3.5 text-sm font-medium transition disabled:cursor-not-allowed disabled:opacity-50"
    :class="{
      'bg-[var(--primary)] text-white hover:brightness-105': variant === 'primary',
      'surface text-[var(--text)] hover:bg-[var(--panel-subtle)]': variant === 'secondary',
      'text-[var(--muted)] hover:bg-[var(--panel-subtle)] hover:text-[var(--text)]': variant === 'ghost',
      'bg-red-600 text-white hover:bg-red-700': variant === 'danger',
    }">
    <slot />
  </Button>
</template>
