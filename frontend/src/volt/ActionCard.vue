<script setup lang="ts">
withDefaults(defineProps<{
  active?: boolean
  disabled?: boolean
  type?: 'button' | 'submit' | 'reset'
}>(), { type: 'button' })
</script>

<template>
  <button
    :type="type"
    :disabled="disabled"
    class="surface focus-ring card-hover block rounded-xl text-left transition-[border-color,background-color,box-shadow,filter,transform] duration-150 hover:brightness-[0.97] active:scale-[0.99] disabled:pointer-events-none disabled:opacity-50"
    :class="active && 'border-[var(--primary)] bg-[var(--primary-soft)]'"
  ><slot /></button>
</template>
