<script setup lang="ts">
import { Check, MousePointer2, X } from 'lucide-vue-next'

defineProps<{ color: string }>()
const emit = defineEmits<{ 'update:color': [color: string]; cancel: [] }>()
</script>

<template>
  <div class="surface flex items-center gap-3 rounded-xl px-3 py-2.5 shadow-xl" role="toolbar" :aria-label="$t('designer.annotationMode')">
    <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><MousePointer2 :size="15" /></span>
    <span class="min-w-0"><span class="block text-xs font-semibold">{{ $t('designer.annotationMode') }}</span><span class="muted mt-0.5 block text-[9px]">{{ $t('designer.annotationModeHint') }}</span></span>
    <div class="flex gap-1.5 border-l border-[var(--border)] pl-3"><button v-for="tone in ['yellow','blue','green','rose']" :key="tone" type="button" class="annotation-swatch" :class="[`annotation-${tone}`, { active: color === tone }]" :aria-label="$t(`designer.noteColors.${tone}`)" @click="emit('update:color', tone)"><Check v-if="color === tone" :size="10" /></button></div>
    <button type="button" class="icon-button ml-1" :aria-label="$t('common.close')" @click="emit('cancel')"><X :size="14" /></button>
  </div>
</template>

<style scoped>
.annotation-swatch { display: flex; width: 24px; height: 24px; align-items: center; justify-content: center; border: 2px solid transparent; border-radius: 6px; color: #344054; }
.annotation-swatch.active { border-color: var(--primary); box-shadow: 0 0 0 2px color-mix(in srgb, var(--primary), transparent 84%); }
.annotation-yellow { background: #fde68a; }.annotation-blue { background: #bfdbfe; }.annotation-green { background: #bbf7d0; }.annotation-rose { background: #fecdd3; }
</style>
