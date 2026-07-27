<script setup lang="ts">
import { AlertCircle, CheckCircle2, Info } from 'lucide-vue-next'
withDefaults(defineProps<{ message?: string; tone?: 'error' | 'success' | 'info' }>(), { message: '', tone: 'info' })
</script>

<template>
  <div v-if="message" class="mt-4 flex items-start gap-2 rounded-lg px-3 py-2 text-sm" :class="tone === 'error' ? 'bg-red-50 text-red-700 dark:bg-red-950/30 dark:text-red-300' : tone === 'success' ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-950/30 dark:text-emerald-300' : 'bg-[var(--primary-soft)] text-[var(--primary)]'">
    <AlertCircle v-if="tone === 'error'" class="mt-0.5 shrink-0" :size="15" /><CheckCircle2 v-else-if="tone === 'success'" class="mt-0.5 shrink-0" :size="15" /><Info v-else class="mt-0.5 shrink-0" :size="15" /><span><slot>{{ message }}</slot></span>
  </div>
</template>
