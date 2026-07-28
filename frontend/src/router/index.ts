import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import AdminUsersPage from '@/pages/AdminUsersPage.vue'; import LoginPage from '@/pages/LoginPage.vue'; import MembersPage from '@/pages/MembersPage.vue'; import ModelsPage from '@/pages/ModelsPage.vue'; import NewWorkspacePage from '@/pages/NewWorkspacePage.vue'; import PublicAppPage from '@/pages/PublicAppPage.vue'; import ScriptsPage from '@/pages/ScriptsPage.vue'; import SettingsPage from '@/pages/SettingsPage.vue'; import StudioPage from '@/pages/StudioPage.vue'; import WorkflowDesignerPage from '@/pages/WorkflowDesignerPage.vue'

const router = createRouter({ history: createWebHistory(), routes: [
  { path: '/login', component: LoginPage, meta: { public: true } },
  { path: '/apps/:slug', component: PublicAppPage, meta: { public: true } },
  { path: '/workspaces/new', component: NewWorkspacePage },
  { path: '/admin/users', component: AdminUsersPage, meta: { platformAdmin: true } },
  { path: '/w/:workspaceId/studio', component: StudioPage },
  { path: '/w/:workspaceId/scripts', component: ScriptsPage },
  { path: '/w/:workspaceId/workflows/:workflowId', component: WorkflowDesignerPage },
  { path: '/w/:workspaceId/members', component: MembersPage },
  { path: '/w/:workspaceId/knowledge', redirect: to => `/w/${String(to.params.workspaceId)}/studio` },
  { path: '/w/:workspaceId/models', component: ModelsPage },
  { path: '/w/:workspaceId/settings', component: SettingsPage },
  { path: '/', redirect: () => {
    const token = localStorage.getItem('access_token')
    const id = localStorage.getItem('workspace_id')
    return token && id ? `/w/${id}/studio` : '/login'
  } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
] })
let sessionHydrated = false
router.beforeEach(async to => {
  const token = localStorage.getItem('access_token')
  const workspaceId = localStorage.getItem('workspace_id')
  if (!to.meta.public && !token) return '/login'
  const auth = useAuthStore()
  if (token && !sessionHydrated) {
    try { await auth.refresh() }
    catch {
      auth.logout()
      if (!to.meta.public) return '/login'
    }
    finally { sessionHydrated = true }
  }
  if (to.meta.platformAdmin) {
    if (!auth.user?.is_platform_admin) return '/'
  }
  if (to.path === '/login' && token && workspaceId) return `/w/${workspaceId}/studio`
  if (to.path === '/login' && token && !workspaceId) {
    localStorage.removeItem('access_token')
    localStorage.removeItem('user')
  }
})
export default router
