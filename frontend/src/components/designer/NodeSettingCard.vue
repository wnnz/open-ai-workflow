<script setup lang="ts">
defineProps<{
  title?: string
  hint?: string
  type?: string
  required?: boolean
  divided?: boolean
}>()
</script>

<template>
  <section class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
    <div v-if="title || hint || $slots.header || $slots.actions" class="flex min-w-0 items-start gap-2">
      <slot name="header">
        <div class="min-w-0 flex-1">
          <div v-if="title" class="flex min-w-0 items-center gap-1.5 text-[11px] font-semibold leading-4">
            <span class="truncate">{{ title }}</span>
            <span v-if="required" class="text-red-500">*</span>
            <span v-if="type" class="ml-auto shrink-0 rounded bg-sky-50 px-1.5 py-0.5 font-mono text-[9px] font-normal text-sky-700 dark:bg-sky-950/40 dark:text-sky-300">{{ type }}</span>
          </div>
          <p v-if="hint" class="muted mt-1 text-[10px] leading-4">{{ hint }}</p>
        </div>
      </slot>
      <div v-if="$slots.actions" class="ml-auto shrink-0"><slot name="actions" /></div>
    </div>
    <div :class="[(title || hint || $slots.header || $slots.actions) && 'mt-3', divided && (title || hint || $slots.header || $slots.actions) && 'border-t border-[var(--border)] pt-3']">
      <slot />
    </div>
  </section>
</template>
