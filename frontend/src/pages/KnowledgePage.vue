<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { BookOpen, FileText, Plus, RefreshCw, Trash2, Upload } from 'lucide-vue-next'
import api from '@/api/client'
import AppShell from '@/components/AppShell.vue'
import { useWorkspacesStore } from '@/stores/workspaces'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import EmptyState from '@/components/ui/EmptyState.vue'
import FormField from '@/components/ui/FormField.vue'
import ModalShell from '@/components/ui/ModalShell.vue'
import PageHeader from '@/components/ui/PageHeader.vue'
import IconButton from '@/volt/IconButton.vue'
import Textarea from '@/volt/Textarea.vue'
import StatusBadge from '@/components/ui/StatusBadge.vue'

const { t } = useI18n(); const workspaces = useWorkspacesStore()
const datasets = ref<any[]>([]); const documents = ref<any[]>([]); const selectedId = ref('')
const showCreate = ref(false); const name = ref(''); const description = ref(''); const loading = ref(false); const error = ref('')
const fileInput = ref<HTMLInputElement | null>(null)
const selected = computed(() => datasets.value.find(item => item.id === selectedId.value))
async function load() { if (!workspaces.activeId) return; error.value = ''; try { datasets.value = (await api.get(`/workspaces/${workspaces.activeId}/knowledge`)).data; if (!datasets.value.some(item => item.id === selectedId.value)) selectedId.value = datasets.value[0]?.id || ''; await loadDocuments() } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) } }
async function loadDocuments() { documents.value = selectedId.value ? (await api.get(`/workspaces/${workspaces.activeId}/knowledge/${selectedId.value}/documents`)).data : [] }
async function create() { loading.value = true; error.value = ''; try { const { data } = await api.post(`/workspaces/${workspaces.activeId}/knowledge`, { name: name.value, description: description.value }); datasets.value.unshift(data); selectedId.value = data.id; showCreate.value = false; name.value = ''; description.value = ''; documents.value = [] } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) } finally { loading.value = false } }
async function upload(event: Event) { const input = event.target as HTMLInputElement; const file = input.files?.[0]; if (!file || !selectedId.value) return; loading.value = true; error.value = ''; try { const form = new FormData(); form.append('file', file); form.append('metadata', '{}'); await api.post(`/workspaces/${workspaces.activeId}/knowledge/${selectedId.value}/documents`, form); await loadDocuments() } catch (cause: any) { error.value = cause.response?.data?.detail || String(cause) } finally { loading.value = false; input.value = '' } }
async function removeDocument(id: string) { if (!confirm(t('knowledge.confirmDocument'))) return; await api.delete(`/workspaces/${workspaces.activeId}/knowledge/${selectedId.value}/documents/${id}`); await loadDocuments() }
async function removeDataset() { if (!selected.value || !confirm(t('knowledge.confirmDataset'))) return; await api.delete(`/workspaces/${workspaces.activeId}/knowledge/${selectedId.value}`); selectedId.value = ''; await load() }
onMounted(load); watch(() => workspaces.activeId, load); watch(selectedId, loadDocuments)
</script>

<template><AppShell><div class="flex h-screen min-h-0 flex-col overflow-hidden px-7 pt-5"><PageHeader :title="t('knowledge.title')" :subtitle="t('knowledge.subtitle')"><template #actions><Button @click="showCreate = true"><Plus :size="16" />{{ t('knowledge.new') }}</Button></template></PageHeader>
<AlertBanner :message="error" tone="error" />
<div class="mt-5 grid min-h-0 flex-1 grid-cols-[280px_minmax(0,1fr)] overflow-hidden rounded-t-lg border border-b-0 border-[var(--border)] bg-[var(--panel)]"><aside class="min-h-0 overflow-y-auto border-r border-[var(--border)] p-3"><button v-for="item in datasets" :key="item.id" class="mb-1 w-full rounded-md px-3 py-2.5 text-left" :class="selectedId === item.id ? 'bg-[var(--primary-soft)] text-[var(--primary)]' : 'hover:bg-[var(--panel-subtle)]'" @click="selectedId = item.id"><div class="truncate text-sm font-medium">{{ item.name }}</div><div class="muted mt-1 truncate text-xs">{{ item.description || t('knowledge.noDescription') }}</div></button><EmptyState v-if="!datasets.length" :title="t('knowledge.empty')" compact><template #icon><BookOpen :size="36" /></template></EmptyState></aside>
<section v-if="selected" class="min-h-0 min-w-0 overflow-y-auto p-5"><div class="flex items-start"><div><h2 class="font-semibold">{{ selected.name }}</h2><p class="muted mt-1 text-sm">{{ selected.description || t('knowledge.noDescription') }}</p></div><div class="ml-auto flex gap-2"><Button variant="secondary" :loading="loading" @click="loadDocuments"><RefreshCw :size="15" />{{ t('common.refresh') }}</Button><input ref="fileInput" class="hidden" type="file" accept=".pdf,.docx,.pptx,.xlsx,.txt,.md,.html,.csv" @change="upload"><Button :loading="loading" @click="fileInput?.click()"><Upload :size="15" />{{ t('knowledge.upload') }}</Button><Button variant="ghost" @click="removeDataset"><Trash2 :size="15" /></Button></div></div>
<div class="mt-5 overflow-hidden rounded-lg border border-[var(--border)]"><div class="grid grid-cols-[minmax(0,1fr)_120px_44px] bg-[var(--panel-subtle)] px-4 py-2 text-xs font-medium"><span>{{ t('knowledge.document') }}</span><span>{{ t('knowledge.status') }}</span><span></span></div><div v-for="doc in documents" :key="doc.id" class="grid grid-cols-[minmax(0,1fr)_120px_44px] items-center border-t border-[var(--border)] px-4 py-3"><div class="flex min-w-0 items-center gap-2"><FileText :size="17" class="shrink-0 text-[var(--primary)]" /><span class="truncate text-sm">{{ doc.name }}</span></div><StatusBadge :label="t(`knowledge.statuses.${doc.status}`)" :tone="doc.status === 'ready' ? 'success' : doc.status === 'failed' ? 'danger' : 'warning'" /><IconButton :label="t('common.delete')" @click="removeDocument(doc.id)"><Trash2 :size="15" /></IconButton></div><EmptyState v-if="!documents.length" :title="t('knowledge.noDocuments')" compact><template #icon><FileText :size="36" /></template></EmptyState></div></section><section v-else class="muted flex items-center justify-center text-sm">{{ t('knowledge.select') }}</section></div>
<ModalShell v-model="showCreate" :title="t('knowledge.new')" form @submit="create"><FormField :label="t('common.name')" required><InputText v-model="name" required /></FormField><FormField class="mt-4" :label="t('common.description')"><Textarea v-model="description" class="h-24" /></FormField><template #footer><Button type="button" variant="secondary" @click="showCreate = false">{{ t('common.cancel') }}</Button><Button type="submit" :loading="loading">{{ t('common.create') }}</Button></template></ModalShell></div></AppShell></template>
