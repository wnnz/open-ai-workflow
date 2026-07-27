<script setup lang="ts">
import { computed, ref } from 'vue'
import { Check, ChevronDown } from 'lucide-vue-next'
const props = defineProps<{ modelValue: string; options: Array<{ value: string; label: string }> }>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
const open = ref(false)
const selected = computed(() => props.options.find(option => option.value === props.modelValue) || props.options[0])
function choose(value: string) { emit('update:modelValue', value); open.value = false }
</script>

<template>
  <div class="relative"><button type="button" class="focus-ring flex h-9 items-center gap-2 rounded-lg bg-[var(--panel-subtle)] px-3 text-sm" :aria-expanded="open" @click="open = !open"><slot name="icon" />{{ selected?.label }}<ChevronDown :size="14" /></button><div v-if="open" class="surface absolute top-11 z-30 min-w-40 rounded-lg p-1 shadow-xl"><button v-for="option in options" :key="option.value" type="button" class="flex w-full items-center gap-2 rounded-md px-2.5 py-2 text-left text-sm hover:bg-[var(--panel-subtle)]" @click="choose(option.value)"><Check :size="14" :class="modelValue === option.value ? 'opacity-100 text-[var(--primary)]' : 'opacity-0'" />{{ option.label }}</button></div></div>
</template>
