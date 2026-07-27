<script setup lang="ts">
import { MessageSquare } from 'lucide-vue-next'

defineProps<{ count: number; selected?: boolean; resolved?: boolean; label: string }>()
defineEmits<{ select: [] }>()
</script>

<template>
  <button type="button" class="comment-pin" :class="{ selected, resolved }" :aria-label="label" @click.stop="$emit('select')">
    <MessageSquare :size="13" />
    <span>{{ count }}</span>
  </button>
</template>

<style scoped>
.comment-pin { display:flex; min-width:30px; height:26px; align-items:center; justify-content:center; gap:3px; border:2px solid white; border-radius:999px; background:#2563eb; color:white; font-size:10px; font-weight:700; box-shadow:0 4px 14px rgb(15 23 42 / .22); transition:transform .15s, opacity .15s; }
.comment-pin:hover,.comment-pin.selected { transform:scale(1.12); }
.comment-pin.resolved { background:#64748b; opacity:.65; }
</style>
