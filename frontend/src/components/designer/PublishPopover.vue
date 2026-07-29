<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Braces, ChevronDown, Clock3, ExternalLink, Globe2, History, KeyRound, Plus, Rocket, Trash2, UserCheck, Users } from 'lucide-vue-next'
import api from '@/api/client'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import IconButton from '@/volt/IconButton.vue'

type PasswordGrant = { id?: string; label: string; password: string; expires_at: string }

const props = withDefaults(defineProps<{
  open: boolean
  workflow: any
  versions: any[]
  publishing?: boolean
}>(), { publishing: false })

const emit = defineEmits<{
  close: []
  publish: [payload: {
    change_note: string
    access: 'public' | 'protected'
    all_users_enabled: boolean
    all_users_expires_at: string | null
    user_grants: Array<{ user_id: string; expires_at: string | null }>
    password_grants: Array<{ id?: string; label: string; password?: string; expires_at: string | null }>
  }]
  history: []
  api: []
  run: []
}>()

const access = ref<'public' | 'protected'>('public')
const changeNote = ref('')
const members = ref<any[]>([])
const allUsersEnabled = ref(false)
const allUsersExpiresAt = ref('')
const userExpiries = ref<Record<string, string>>({})
const passwordGrants = ref<PasswordGrant[]>([])
const latest = computed(() => props.versions[0] || null)
const hasProtectedGrant = computed(() => allUsersEnabled.value || Object.keys(userExpiries.value).length > 0 || passwordGrants.value.length > 0)
const passwordsValid = computed(() => passwordGrants.value.every(item => Boolean(item.id || item.password)))
const canPublish = computed(() => access.value === 'public' || (hasProtectedGrant.value && passwordsValid.value))

function toLocalInput(value?: string | null) {
  if (!value) return ''
  const date = new Date(value)
  const offset = date.getTimezoneOffset() * 60000
  return new Date(date.getTime() - offset).toISOString().slice(0, 16)
}

function toIso(value: string) {
  return value ? new Date(value).toISOString() : null
}

async function loadAccessConfiguration() {
  if (!props.workflow?.id || !props.workflow?.workspace_id) return
  access.value = props.workflow.published_access === 'protected' ? 'protected' : 'public'
  changeNote.value = ''
  const [memberResponse, grantResponse] = await Promise.all([
    api.get(`/workspaces/${props.workflow.workspace_id}/members`),
    api.get(`/workspaces/${props.workflow.workspace_id}/workflows/${props.workflow.id}/access-grants`),
  ])
  members.value = memberResponse.data
  const grants = grantResponse.data as any[]
  const allUsers = grants.find(item => item.grant_type === 'all_users')
  allUsersEnabled.value = Boolean(allUsers)
  allUsersExpiresAt.value = toLocalInput(allUsers?.expires_at)
  userExpiries.value = Object.fromEntries(
    grants.filter(item => item.grant_type === 'user').map(item => [item.user_id, toLocalInput(item.expires_at)]),
  )
  passwordGrants.value = grants
    .filter(item => item.grant_type === 'password')
    .map(item => ({ id: item.id, label: item.label, password: '', expires_at: toLocalInput(item.expires_at) }))
  if (access.value === 'protected' && !grants.length) allUsersEnabled.value = true
}

watch(() => [props.open, props.workflow?.id], ([open]) => {
  if (open) void loadAccessConfiguration()
}, { immediate: true })

watch(() => props.publishing, (publishing, previous) => {
  if (previous && !publishing && props.open) void loadAccessConfiguration()
})

watch(access, value => {
  if (value === 'protected' && !hasProtectedGrant.value) allUsersEnabled.value = true
})

function toggleUser(userId: string, enabled: boolean) {
  const next = { ...userExpiries.value }
  if (enabled) next[userId] = ''
  else delete next[userId]
  userExpiries.value = next
}

function addPasswordGrant() {
  passwordGrants.value.push({ label: '', password: '', expires_at: '' })
}

function submit() {
  if (!canPublish.value) return
  emit('publish', {
    access: access.value,
    change_note: changeNote.value.trim() || (props.workflow?.published_version_id ? 'Published update' : 'Initial publish'),
    all_users_enabled: access.value === 'protected' && allUsersEnabled.value,
    all_users_expires_at: access.value === 'protected' && allUsersEnabled.value ? toIso(allUsersExpiresAt.value) : null,
    user_grants: access.value === 'protected'
      ? Object.entries(userExpiries.value).map(([user_id, expires_at]) => ({ user_id, expires_at: toIso(expires_at) }))
      : [],
    password_grants: access.value === 'protected'
      ? passwordGrants.value.map(item => ({
          ...(item.id ? { id: item.id } : {}),
          label: item.label.trim(),
          ...(item.password ? { password: item.password } : {}),
          expires_at: toIso(item.expires_at),
        }))
      : [],
  })
}
</script>

<template>
  <section v-if="open" class="surface rounded-lg">
    <header class="flex items-center gap-3 border-b border-[var(--border)] px-5 py-4">
      <span class="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><Rocket :size="17" /></span>
      <div class="min-w-0 flex-1"><h2 class="text-sm font-semibold">{{ $t('designer.publishApp') }}</h2><p class="muted mt-0.5 text-xs">{{ $t('designer.publishAppHint') }}</p></div>
    </header>

    <div class="p-5">
      <div v-if="latest" class="mb-4 flex items-center gap-3 border-b border-[var(--border)] pb-4">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-[11px] font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">v{{ latest.version }}</span>
        <span class="min-w-0 flex-1"><span class="block text-xs font-semibold">{{ $t('designer.latestPublished') }}</span><span class="muted mt-0.5 flex items-center gap-1 text-[10px]"><Clock3 :size="10" />{{ new Date(latest.created_at).toLocaleString() }}</span></span>
      </div>

      <div class="grid gap-3 sm:grid-cols-[180px_minmax(0,1fr)]">
        <Select v-model="access" class="!h-9 !text-xs" :aria-label="$t('designer.accessMode')"><option value="public">{{ $t('designer.publicAccess') }}</option><option value="protected">{{ $t('designer.protectedAccess') }}</option></Select>
        <InputText v-model="changeNote" class="!h-9 !text-xs" :placeholder="$t('designer.changeNotePlaceholder')" />
      </div>
      <p class="muted mt-2 text-xs leading-5">{{ access === 'protected' ? $t('designer.protectedAccessHint') : $t('designer.publicAccessHint') }}</p>

      <div v-if="access === 'protected'" class="mt-5 border-t border-[var(--border)] pt-5">
        <h3 class="mb-2 text-xs font-semibold text-[var(--muted)]">{{ $t('designer.accessGrants') }}</h3>
        <div class="access-list divide-y divide-[var(--border)] overflow-hidden rounded-lg border border-[var(--border)]">
          <section class="access-row">
            <span class="access-icon"><Users :size="17" /></span>
            <label class="min-w-0 flex-1 cursor-pointer"><span class="block text-sm font-medium">{{ $t('designer.allSignedInUsers') }}</span><span class="muted mt-0.5 block text-xs">{{ $t('designer.allSignedInUsersHint') }}</span></label>
            <InputText v-if="allUsersEnabled" v-model="allUsersExpiresAt" class="!w-56" type="datetime-local" :aria-label="$t('designer.expiresAt')" />
            <input v-model="allUsersEnabled" class="h-4 w-4 shrink-0 accent-[var(--primary)]" type="checkbox" :aria-label="$t('designer.allSignedInUsers')" />
          </section>

          <details class="access-details">
            <summary class="access-row cursor-pointer list-none">
              <span class="access-icon"><UserCheck :size="17" /></span>
              <span class="min-w-0 flex-1"><span class="block text-sm font-medium">{{ $t('designer.specificUsers') }}</span><span class="muted mt-0.5 block text-xs">{{ $t('designer.specificUsersHint') }}</span></span>
              <span v-if="Object.keys(userExpiries).length" class="access-count">{{ Object.keys(userExpiries).length }}</span>
              <ChevronDown class="details-chevron text-[var(--muted)]" :size="16" />
            </summary>
            <div class="divide-y divide-[var(--border)] border-t border-[var(--border)] bg-[var(--panel-subtle)]">
              <div v-for="member in members" :key="member.user.id" class="grid items-center gap-3 px-4 py-2.5 sm:grid-cols-[minmax(0,1fr)_220px]">
                <label class="flex min-w-0 items-center gap-2.5"><input :checked="Object.hasOwn(userExpiries, member.user.id)" class="h-4 w-4 accent-[var(--primary)]" type="checkbox" @change="toggleUser(member.user.id, ($event.target as HTMLInputElement).checked)" /><span class="min-w-0"><span class="block truncate text-xs font-medium">{{ member.user.display_name }}</span><span class="muted block truncate text-[10px]">{{ member.user.email }}</span></span></label>
                <InputText v-if="Object.hasOwn(userExpiries, member.user.id)" v-model="userExpiries[member.user.id]" type="datetime-local" :aria-label="$t('designer.userExpiry', { name: member.user.display_name })" />
              </div>
            </div>
          </details>

          <details class="access-details">
            <summary class="access-row cursor-pointer list-none">
              <span class="access-icon"><KeyRound :size="17" /></span>
              <span class="min-w-0 flex-1"><span class="block text-sm font-medium">{{ $t('designer.passwordAccess') }}</span><span class="muted mt-0.5 block text-xs">{{ $t('designer.passwordAccessHint') }}</span></span>
              <span v-if="passwordGrants.length" class="access-count">{{ passwordGrants.length }}</span>
              <ChevronDown class="details-chevron text-[var(--muted)]" :size="16" />
            </summary>
            <div class="border-t border-[var(--border)] bg-[var(--panel-subtle)] p-3">
              <div v-if="passwordGrants.length" class="divide-y divide-[var(--border)] rounded-md border border-[var(--border)] bg-[var(--panel)]">
                <div v-for="(grant, index) in passwordGrants" :key="grant.id || index" class="grid gap-2 p-3 sm:grid-cols-[minmax(120px,0.7fr)_minmax(150px,1fr)_minmax(190px,1fr)_36px]">
                  <InputText v-model="grant.label" :placeholder="$t('designer.passwordLabel')" />
                  <InputText v-model="grant.password" type="password" :placeholder="grant.id ? $t('designer.keepExistingPassword') : $t('designer.accessPassword')" />
                  <InputText v-model="grant.expires_at" type="datetime-local" :aria-label="$t('designer.passwordExpiry', { index: index + 1 })" />
                  <IconButton :label="$t('common.delete')" tone="danger" @click="passwordGrants.splice(index, 1)"><Trash2 :size="14" /></IconButton>
                </div>
              </div>
              <Button class="mt-3" variant="secondary" @click="addPasswordGrant"><Plus :size="14" />{{ $t('designer.addPassword') }}</Button>
            </div>
          </details>
        </div>
      </div>

      <Button class="mt-5 w-full" :loading="publishing" :disabled="!canPublish" @click="submit"><Rocket :size="14" />{{ workflow?.published_version_id ? $t('designer.publishUpdate') : $t('workflow.publish') }}</Button>

        <div v-if="workflow?.published_version_id" class="mt-4 grid gap-2 border-t border-[var(--border)] pt-4 sm:grid-cols-3">
          <button type="button" class="publish-shortcut" @click="emit('run')"><Globe2 :size="15" /><span>{{ $t('designer.openPublishedApp') }}</span><ExternalLink :size="11" class="ml-auto" /></button>
          <button type="button" class="publish-shortcut" @click="emit('api')"><Braces :size="15" /><span>{{ $t('designer.apiAccess') }}</span></button>
          <button type="button" class="publish-shortcut" @click="emit('history')"><History :size="15" /><span>{{ $t('designer.versionHistory') }}</span></button>
        </div>
    </div>
  </section>
</template>

<style scoped>
.publish-shortcut { display: flex; height: 38px; align-items: center; gap: 8px; border: 1px solid var(--border); border-radius: 8px; padding: 0 10px; color: var(--muted); font-size: 11px; text-align: left; }
button.publish-shortcut:hover { background: var(--panel-subtle); color: var(--text); }
.access-row { display: flex; min-height: 68px; align-items: center; gap: 12px; padding: 10px 14px; }
.access-icon { display: flex; height: 34px; width: 34px; flex: 0 0 auto; align-items: center; justify-content: center; border-radius: 7px; background: var(--primary-soft); color: var(--primary); }
.access-count { min-width: 24px; border-radius: 999px; background: var(--primary-soft); padding: 2px 7px; color: var(--primary); font-size: 11px; font-weight: 600; text-align: center; }
.access-details[open] .details-chevron { transform: rotate(180deg); }
.details-chevron { transition: transform 150ms ease; }
</style>
