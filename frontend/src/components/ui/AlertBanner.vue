<script setup lang="ts">
import { useToastMessage } from '@/composables/useToast'

const props = withDefaults(defineProps<{ message?: string; tone?: 'error' | 'success' | 'info' }>(), { message: '', tone: 'info' })
useToastMessage(() => props.message, props.tone)
</script>

<template><span v-if="false" /></template>
