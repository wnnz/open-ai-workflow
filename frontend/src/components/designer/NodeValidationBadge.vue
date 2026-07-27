<script setup lang="ts">
import { AlertTriangle } from 'lucide-vue-next'

defineProps<{ messages: string[] }>()
const emit = defineEmits<{ focus: [] }>()
</script>

<template>
  <button v-if="messages.length" type="button" class="validation-badge nodrag nopan" :aria-label="$t('designer.nodeIssueCount', { count: messages.length })" :title="messages.join('\n')" @click.stop="emit('focus')">
    <AlertTriangle :size="11" /><span>{{ messages.length }}</span>
  </button>
</template>

<style scoped>
.validation-badge { position: absolute; left: -9px; top: -9px; z-index: 15; display: flex; min-width: 22px; height: 22px; align-items: center; justify-content: center; gap: 2px; border: 1px solid #fdb022; border-radius: 999px; background: #fffaeb; padding: 0 5px; color: #b54708; font-size: 9px; font-weight: 700; box-shadow: 0 2px 7px rgb(16 24 40 / 14%); }
.validation-badge:hover { border-color: #f79009; background: #fef0c7; transform: scale(1.05); }
:global(.dark) .validation-badge { border-color: #b54708; background: #451a03; color: #fcd34d; }
</style>
