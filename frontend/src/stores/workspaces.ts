import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import api from '@/api/client'

export interface Workspace { id: string; name: string; slug: string; role: string; icon?: string; description?: string; timezone?: string; version: number; is_archived: boolean }
export const useWorkspacesStore = defineStore('workspaces', () => {
  const items = ref<Workspace[]>([])
  const activeId = ref(localStorage.getItem('workspace_id'))
  const active = computed(() => items.value.find(item => item.id === activeId.value) || items.value[0])
  async function load() {
    const { data } = await api.get('/workspaces'); items.value = data
    if (!items.value.some(item => item.id === activeId.value) && items.value[0]) select(items.value[0].id)
  }
  function select(id: string) { activeId.value = id; localStorage.setItem('workspace_id', id) }
  async function create(name: string) { const { data } = await api.post('/workspaces', { name }); items.value.push(data); select(data.id) }
  return { items, activeId, active, load, select, create }
})
