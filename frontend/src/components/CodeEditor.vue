<script setup lang="ts">
import { computed, defineAsyncComponent } from 'vue'
import { usePreferencesStore } from '@/stores/preferences'

declare global {
  interface Window { MonacoEnvironment?: { getWorker: () => Worker } }
}

const AsyncMonacoEditor = defineAsyncComponent({
  loader: async () => {
    const [{ VueMonacoEditor, loader }, monaco, worker] = await Promise.all([
      import('@guolao/vue-monaco-editor'),
      import('monaco-editor/esm/vs/editor/editor.api'),
      import('monaco-editor/esm/vs/editor/editor.worker?worker'),
      import('monaco-python'),
    ])
    if (!window.MonacoEnvironment) {
      window.MonacoEnvironment = { getWorker: () => new worker.default() }
    }
    loader.config({ monaco })
    return VueMonacoEditor
  },
  delay: 100,
  timeout: 30_000,
})

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
    <AsyncMonacoEditor :value="modelValue" :language="language" :theme="theme" :options="{ ...options, readOnly }" @update:value="emit('update:modelValue', $event || '')" @focus="emit('focus')" @blur="emit('blur')" />
  </div>
</template>
