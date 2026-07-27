<script setup lang="ts">
import { AlertTriangle, Check, LoaderCircle, RefreshCw, RotateCcw, Timer } from 'lucide-vue-next'

type WorkflowSaveState = 'idle' | 'dirty' | 'saving' | 'saved' | 'error' | 'conflict'

defineProps<{
  state: WorkflowSaveState
  savedAt?: Date | null
  error?: string
}>()

const emit = defineEmits<{ retry: []; reload: [] }>()
</script>

<template>
  <div class="flex min-w-0 items-center gap-1.5 text-xs" :class="state === 'error' || state === 'conflict' ? 'text-red-600 dark:text-red-400' : 'text-[var(--muted)]'" role="status" aria-live="polite">
    <LoaderCircle v-if="state === 'saving'" :size="13" class="animate-spin text-[var(--primary)]" />
    <Timer v-else-if="state === 'dirty'" :size="13" class="text-amber-600" />
    <AlertTriangle v-else-if="state === 'error' || state === 'conflict'" :size="13" />
    <Check v-else :size="13" class="text-emerald-600" />

    <span v-if="state === 'saving'">{{ $t('designer.saving') }}</span>
    <span v-else-if="state === 'dirty'">{{ $t('designer.waitingToSave') }}</span>
    <span v-else-if="state === 'error'" class="max-w-72 truncate" :title="error">{{ $t('designer.saveFailed') }}</span>
    <span v-else-if="state === 'conflict'" class="max-w-72 truncate" :title="error">{{ $t('designer.saveConflict') }}</span>
    <span v-else-if="savedAt">{{ $t('designer.savedAt') }} {{ savedAt.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) }}</span>
    <span v-else>{{ $t('designer.autoSave') }}</span>

    <button v-if="state === 'error'" type="button" class="inline-flex items-center gap-1 font-medium underline decoration-dotted underline-offset-2 hover:text-red-700" @click="emit('retry')">
      <RefreshCw :size="11" />{{ $t('common.retry') }}
    </button>
    <button v-else-if="state === 'conflict'" type="button" class="inline-flex items-center gap-1 font-medium underline decoration-dotted underline-offset-2 hover:text-red-700" @click="emit('reload')">
      <RotateCcw :size="11" />{{ $t('designer.reloadDraft') }}
    </button>
  </div>
</template>
