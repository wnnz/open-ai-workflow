<script setup lang="ts">
import { AlertCircle, CheckCircle2, Info, X } from 'lucide-vue-next'
import { dismissToast, toastMessages } from '@/composables/useToast'
</script>

<template>
  <Teleport to="body">
    <div class="pointer-events-none fixed inset-x-0 top-4 z-[200] flex flex-col items-center gap-2 px-4" aria-live="polite" aria-atomic="false">
      <TransitionGroup name="toast">
        <div
          v-for="toast in toastMessages"
          :key="toast.id"
          class="pointer-events-auto flex w-full max-w-lg items-start gap-3 rounded-lg border bg-[var(--panel)] px-4 py-3 text-sm shadow-lg shadow-slate-900/10"
          :class="toast.tone === 'error' ? 'border-red-200 text-red-700 dark:border-red-900 dark:text-red-300' : toast.tone === 'success' ? 'border-emerald-200 text-emerald-700 dark:border-emerald-900 dark:text-emerald-300' : 'border-[var(--border)] text-[var(--text)]'"
          :role="toast.tone === 'error' ? 'alert' : 'status'"
        >
          <AlertCircle v-if="toast.tone === 'error'" class="mt-0.5 shrink-0" :size="17" />
          <CheckCircle2 v-else-if="toast.tone === 'success'" class="mt-0.5 shrink-0" :size="17" />
          <Info v-else class="mt-0.5 shrink-0 text-[var(--primary)]" :size="17" />
          <span class="min-w-0 flex-1 break-words leading-5">{{ toast.message }}</span>
          <button type="button" class="-mr-1 flex h-6 w-6 shrink-0 items-center justify-center rounded-md opacity-60 hover:bg-black/5 hover:opacity-100 dark:hover:bg-white/10" :aria-label="$t('common.close')" @click="dismissToast(toast.id)"><X :size="14" /></button>
        </div>
      </TransitionGroup>
    </div>
  </Teleport>
</template>

<style scoped>
.toast-enter-active,.toast-leave-active { transition: opacity 180ms ease, transform 180ms ease; }
.toast-enter-from,.toast-leave-to { opacity: 0; transform: translateY(-10px); }
.toast-move { transition: transform 180ms ease; }
</style>
