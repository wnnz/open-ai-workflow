<script setup lang="ts">
import { X } from 'lucide-vue-next'
import IconButton from '@/volt/IconButton.vue'
withDefaults(defineProps<{ modelValue: boolean; title: string; description?: string; maxWidth?: string; panelClass?: string; bodyClass?: string; form?: boolean }>(), { description: '', maxWidth: 'max-w-lg', panelClass: '', bodyClass: 'p-5', form: false })
const emit = defineEmits<{ 'update:modelValue': [value: boolean]; submit: [] }>()
function close() { emit('update:modelValue', false) }
</script>

<template>
  <Teleport to="body">
    <div v-if="modelValue" class="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/40 p-5" role="presentation" @mousedown.self="close">
      <component :is="form ? 'form' : 'section'" class="surface flex max-h-[92vh] w-full flex-col overflow-hidden rounded-xl shadow-2xl" :class="[maxWidth, panelClass]" role="dialog" aria-modal="true" :aria-label="title" @submit.prevent="emit('submit')">
        <header class="flex shrink-0 items-start gap-3 border-b border-[var(--border)] px-5 py-4"><div class="min-w-0 flex-1"><h2 class="font-semibold">{{ title }}</h2><p v-if="description" class="muted mt-1 text-xs">{{ description }}</p></div><IconButton :label="$t('common.close')" @click="close"><X :size="16" /></IconButton></header>
        <div class="min-h-0 flex-1 overflow-y-auto" :class="bodyClass"><slot /></div>
        <footer v-if="$slots.footer" class="flex shrink-0 justify-end gap-2 border-t border-[var(--border)] px-5 py-4"><slot name="footer" /></footer>
      </component>
    </div>
  </Teleport>
</template>
