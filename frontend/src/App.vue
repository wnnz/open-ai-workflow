<script setup lang="ts">
import { onMounted } from 'vue'
import { RouterView } from 'vue-router'
import ToastContainer from '@/components/ui/ToastContainer.vue'
import { usePreferencesStore } from '@/stores/preferences'

const preferences = usePreferencesStore()
onMounted(() => preferences.applyTheme())
</script>

<template><RouterView /><ToastContainer /></template>
