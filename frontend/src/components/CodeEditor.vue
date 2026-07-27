<script setup lang="ts">
import { computed } from 'vue'
import { VueMonacoEditor, loader } from '@guolao/vue-monaco-editor'
import * as monaco from 'monaco-editor/esm/vs/editor/editor.api'
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker'
import 'monaco-python'
import { usePreferencesStore } from '@/stores/preferences'

declare global {
  interface Window { MonacoEnvironment?: { getWorker: () => Worker } }
}

if (!window.MonacoEnvironment) window.MonacoEnvironment = { getWorker: () => new editorWorker() }
loader.config({ monaco })

withDefaults(defineProps<{ modelValue: string; language?: string; height?: string; readOnly?: boolean }>(), {
  language: 'python', height: '320px', readOnly: false,
})
const emit = defineEmits<{ 'update:modelValue': [value: string]; focus: []; blur: [] }>()
const preferences = usePreferencesStore()
const theme = computed(() => preferences.isDark ? 'vs-dark' : 'vs')
const options = computed(() => ({
  automaticLayout: true,
  minimap: { enabled: false },
  fontSize: 12,
  lineHeight: 20,
  fontFamily: 'JetBrains Mono, Cascadia Code, Consolas, monospace',
  scrollBeyondLastLine: false,
  wordWrap: 'on' as const,
  tabSize: 4,
  insertSpaces: true,
  padding: { top: 10, bottom: 10 },
  readOnly: false,
  renderLineHighlight: 'line' as const,
}))
</script>

<template>
  <div data-testid="code-editor" class="overflow-hidden rounded-lg border border-[var(--border)]" :style="{ height }">
    <VueMonacoEditor :value="modelValue" :language="language" :theme="theme" :options="{ ...options, readOnly }" @update:value="emit('update:modelValue', $event || '')" @focus="emit('focus')" @blur="emit('blur')" />
  </div>
</template>
