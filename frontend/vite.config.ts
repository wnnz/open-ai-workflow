import path from 'node:path'
import tailwindcss from '@tailwindcss/vite'
import vue from '@vitejs/plugin-vue'
import { defineConfig } from 'vite'

export default defineConfig({
  plugins: [vue(), tailwindcss()],
  resolve: { alias: {
    '@': path.resolve(__dirname, './src'),
    'monaco-python': path.resolve(__dirname, './node_modules/monaco-editor/esm/vs/basic-languages/python/python.contribution.js'),
  } },
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000', '/v1': 'http://localhost:8000' },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          'vue-runtime': ['vue', 'vue-i18n', 'vue-router', 'pinia'],
          'workflow-canvas': [
            '@vue-flow/core',
            '@vue-flow/background',
            '@vue-flow/controls',
            '@vue-flow/minimap',
          ],
        },
      },
    },
  },
})
