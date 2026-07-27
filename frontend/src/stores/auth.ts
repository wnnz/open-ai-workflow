import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '@/api/client'

export interface User { id: string; email: string; display_name: string; is_active: boolean; is_platform_admin: boolean }
function storedUser(): User | null {
  try { return JSON.parse(localStorage.getItem('user') || 'null') }
  catch { localStorage.removeItem('user'); return null }
}
export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('access_token'))
  const user = ref<User | null>(storedUser())
  const authenticated = computed(() => Boolean(token.value))
  async function login(email: string, password: string) {
    const { data } = await api.post('/auth/login', { email, password })
    setSession(data)
  }
  async function register(email: string, password: string, display_name: string) {
    const { data } = await api.post('/auth/register', { email, password, display_name })
    setSession(data)
  }
  async function refresh() {
    if (!token.value) return null
    const { data } = await api.get<User>('/auth/me')
    user.value = data
    localStorage.setItem('user', JSON.stringify(data))
    return data
  }
  function setSession(data: { access_token: string; user: User }) {
    token.value = data.access_token; user.value = data.user
    localStorage.setItem('access_token', data.access_token); localStorage.setItem('user', JSON.stringify(data.user))
  }
  function logout() { token.value = null; user.value = null; localStorage.removeItem('access_token'); localStorage.removeItem('user') }
  return { token, user, authenticated, login, register, refresh, logout }
})
