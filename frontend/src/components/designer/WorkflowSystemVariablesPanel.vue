<script setup lang="ts">
import { Check, Copy, X } from 'lucide-vue-next'
import { ref } from 'vue'
import { SYSTEM_VARIABLES } from '@/types/workflowSystemVariables'

defineEmits<{ close: [] }>()
const copied = ref('')
async function copyReference(name: string) {
  await navigator.clipboard.writeText(`{{sys.${name}}}`)
  copied.value = name
  setTimeout(() => { if (copied.value === name) copied.value = '' }, 1200)
}
</script>

<template>
  <div class="surface absolute right-0 top-10 z-50 w-[370px] overflow-hidden rounded-xl shadow-2xl" role="dialog" :aria-label="$t('designer.systemVariables')">
    <header class="flex items-start gap-3 border-b border-[var(--border)] px-4 py-3.5"><span class="flex h-8 w-8 items-center justify-center rounded-lg bg-violet-50 font-mono text-[11px] font-bold text-violet-600 dark:bg-violet-950/30 dark:text-violet-300">{x}</span><div class="min-w-0 flex-1"><h2 class="text-sm font-semibold">{{ $t('designer.systemVariables') }}</h2><p class="muted mt-1 text-[10px] leading-4">{{ $t('designer.systemVariablesHint') }}</p></div><button type="button" class="icon-button" :aria-label="$t('common.close')" @click="$emit('close')"><X :size="15" /></button></header>
    <div class="p-2">
      <button v-for="variable in SYSTEM_VARIABLES" :key="variable.name" type="button" class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left hover:bg-[var(--panel-subtle)]" :aria-label="$t('designer.copySystemVariable', { name: variable.name })" @click="copyReference(variable.name)">
        <span class="flex h-7 w-7 items-center justify-center rounded-md bg-[var(--panel-subtle)] font-mono text-[10px] text-violet-600">sys</span><span class="min-w-0 flex-1"><code class="block text-[11px] font-semibold">sys.{{ variable.name }}</code><span class="muted mt-0.5 block text-[9px]">{{ $t(`designer.systemVariableDescriptions.${variable.name}`) }}</span></span><span class="rounded bg-[var(--panel-subtle)] px-1.5 py-0.5 text-[9px] text-[var(--muted)]">{{ variable.type }}</span><Check v-if="copied === variable.name" :size="13" class="text-emerald-600" /><Copy v-else :size="12" class="muted" />
      </button>
    </div>
  </div>
</template>

