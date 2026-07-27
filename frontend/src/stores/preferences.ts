import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { i18n, type Locale } from '@/i18n'

export type Theme = 'light' | 'dark' | 'system'

export const usePreferencesStore = defineStore('preferences', () => {
  const theme = ref<Theme>((localStorage.getItem('theme') as Theme) || 'system')
  const locale = ref<Locale>((localStorage.getItem('locale') as Locale) || 'zh')
  const isDark = computed(() => theme.value === 'dark' || (theme.value === 'system' && matchMedia('(prefers-color-scheme: dark)').matches))

  function applyTheme() {
    document.documentElement.classList.toggle('dark', isDark.value)
    document.documentElement.lang = locale.value === 'zh' ? 'zh-CN' : 'en'
  }
  function setTheme(value: Theme) {
    theme.value = value
    localStorage.setItem('theme', value)
    applyTheme()
  }
  function setLocale(value: Locale) {
    locale.value = value
    localStorage.setItem('locale', value)
    i18n.global.locale.value = value
    applyTheme()
  }
  return { theme, locale, isDark, applyTheme, setTheme, setLocale }
})
