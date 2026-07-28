<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { RouterLink, useRoute, useRouter } from 'vue-router'
import { Bot, Boxes, ChevronDown, FileCode2, Languages, LogOut, Moon, Settings, ShieldCheck, Sun, Users, Workflow } from 'lucide-vue-next'
import Button from '@/volt/Button.vue'
import api from '@/api/client'
import { useAuthStore } from '@/stores/auth'
import { usePreferencesStore } from '@/stores/preferences'
import { useWorkspacesStore } from '@/stores/workspaces'

const { t } = useI18n()
const route = useRoute(); const router = useRouter()
const auth = useAuthStore(); const workspaces = useWorkspacesStore(); const preferences = usePreferencesStore()
const workspaceOpen = ref(false); const userOpen = ref(false)
const publishedApps = ref<any[]>([])
const activeBase = computed(() => `/w/${workspaces.activeId || ''}`)
const nav = computed(() => [
  { label: t('nav.studio'), icon: Workflow, path: `${activeBase.value}/studio` },
  { label: t('nav.scripts'), icon: FileCode2, path: `${activeBase.value}/scripts` },
  { label: t('nav.models'), icon: Bot, path: `${activeBase.value}/models` },
  { label: t('nav.members'), icon: Users, path: `${activeBase.value}/members` },
  { label: t('nav.settings'), icon: Settings, path: `${activeBase.value}/settings` },
  ...(auth.user?.is_platform_admin ? [{ label: t('nav.userAdmin'), icon: ShieldCheck, path: '/admin/users' }] : []),
])
onMounted(async () => {
  const routeWorkspace = String(route.params.workspaceId || '')
  if (routeWorkspace) workspaces.select(routeWorkspace)
  await workspaces.load()
  await loadPublishedApps()
})
async function loadPublishedApps() { if (!workspaces.activeId) return; const { data } = await api.get(`/workspaces/${workspaces.activeId}/workflows`); publishedApps.value = data.filter((item: any) => item.published_version_id) }
function switchWorkspace(id: string) {
  workspaces.select(id); workspaceOpen.value = false
  const section = route.path.split('/')[3] || 'studio'; router.push(`/w/${id}/${section}`)
}
function toggleTheme() { preferences.setTheme(preferences.isDark ? 'light' : 'dark') }
function toggleLocale() { preferences.setLocale(preferences.locale === 'zh' ? 'en' : 'zh') }
function logout() { auth.logout(); router.push('/login') }
watch(() => workspaces.activeId, loadPublishedApps)
</script>

<template>
  <div class="flex min-h-screen bg-[var(--app-bg)]">
    <aside class="fixed inset-y-0 left-0 z-30 flex w-64 flex-col border-r border-[var(--border)] bg-[var(--panel-subtle)] p-3">
      <div class="flex h-10 items-center gap-2 px-2 text-lg font-bold tracking-tight">
        <span class="flex h-7 w-7 items-center justify-center rounded-lg bg-[var(--primary)] text-sm text-white">O</span>
        <span>Open Workflow</span>
      </div>
      <div class="relative mt-3">
        <button class="surface focus-ring flex h-10 w-full items-center gap-2 rounded-xl px-2.5 text-left text-sm" @click="workspaceOpen = !workspaceOpen">
          <span class="flex h-6 w-6 shrink-0 items-center justify-center rounded-md bg-orange-500 text-xs font-semibold text-white">{{ workspaces.active?.name?.[0] || 'W' }}</span>
          <span class="min-w-0 flex-1 truncate">{{ workspaces.active?.name || t('workspace.personal') }}</span><ChevronDown :size="15" class="muted" />
        </button>
        <div v-if="workspaceOpen" class="surface absolute left-0 right-0 top-11 z-50 rounded-xl p-1.5 shadow-xl">
          <button v-for="item in workspaces.items" :key="item.id" class="flex w-full items-center rounded-lg px-2.5 py-2 text-left text-sm hover:bg-[var(--panel-subtle)]" @click="switchWorkspace(item.id)">{{ item.name }}</button>
          <button class="mt-1 w-full border-t border-[var(--border)] px-2.5 pt-2 text-left text-sm text-[var(--primary)]" @click="$router.push('/workspaces/new')">+ {{ t('workspace.create') }}</button>
        </div>
      </div>
      <nav class="mt-4 space-y-1">
        <RouterLink v-for="item in nav" :key="item.path" :to="item.path"
          class="flex h-9 items-center gap-2.5 rounded-lg px-2.5 text-sm text-[var(--muted)] transition hover:bg-[var(--panel)] hover:text-[var(--text)]"
          active-class="!bg-[var(--primary-soft)] !text-[var(--primary)] font-medium">
          <component :is="item.icon" :size="17" /><span>{{ item.label }}</span>
        </RouterLink>
      </nav>
      <div class="mt-5 px-2 text-[11px] font-medium uppercase tracking-wider text-[var(--muted)]">{{ t('nav.publishedApps') }}</div>
      <RouterLink v-for="app in publishedApps" :key="app.id" :to="`/w/${workspaces.activeId}/workflows/${app.id}`" class="mt-1 flex items-center gap-2 rounded-lg px-2 py-1.5 text-sm hover:bg-[var(--panel)]"><Boxes :size="16" class="shrink-0 text-violet-500" /><span class="truncate">{{ app.name }}</span></RouterLink>
      <div v-if="!publishedApps.length" class="muted px-2 py-2 text-xs">{{ t('nav.noPublishedApps') }}</div>
      <div class="mt-auto flex items-center justify-between">
        <div class="relative">
          <button class="flex items-center gap-2 rounded-lg p-1.5 hover:bg-[var(--panel)]" @click="userOpen = !userOpen">
            <span class="flex h-7 w-7 items-center justify-center rounded-full bg-[var(--primary)] text-xs font-semibold text-white">{{ auth.user?.display_name?.[0]?.toUpperCase() }}</span>
            <span class="max-w-32 truncate text-sm">{{ auth.user?.display_name }}</span>
            <span v-if="auth.user?.is_platform_admin" class="rounded bg-[var(--primary-soft)] px-1.5 py-0.5 text-[10px] font-medium text-[var(--primary)]">{{ t('admin.badge') }}</span>
          </button>
          <div v-if="userOpen" class="surface absolute bottom-10 left-0 w-52 rounded-xl p-1.5 shadow-xl">
            <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm hover:bg-[var(--panel-subtle)]" @click="toggleLocale"><Languages :size="16" />{{ preferences.locale === 'zh' ? 'English' : '简体中文' }}</button>
            <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm hover:bg-[var(--panel-subtle)]" @click="toggleTheme"><Sun v-if="preferences.isDark" :size="16" /><Moon v-else :size="16" />{{ preferences.isDark ? t('common.light') : t('common.dark') }}</button>
            <button class="flex w-full items-center gap-2 rounded-lg px-2.5 py-2 text-sm text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30" @click="logout"><LogOut :size="16" />{{ t('auth.logout') }}</button>
          </div>
        </div>
        <div class="flex"><Button data-testid="locale-toggle" :aria-label="preferences.locale === 'zh' ? 'Switch to English' : '切换到中文'" variant="ghost" class="!w-9 !px-0" @click="toggleLocale"><Languages :size="16" /></Button><Button data-testid="theme-toggle" :aria-label="preferences.isDark ? t('common.light') : t('common.dark')" variant="ghost" class="!w-9 !px-0" @click="toggleTheme"><Sun v-if="preferences.isDark" :size="16" /><Moon v-else :size="16" /></Button></div>
      </div>
    </aside>
    <main class="ml-64 min-h-screen flex-1"><slot /></main>
  </div>
</template>
