<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { Braces, Clock3, ExternalLink, FileClock, Globe2, History, KeyRound, Rocket, X } from 'lucide-vue-next'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'

const props = withDefaults(defineProps<{
  open: boolean
  workflow: any
  versions: any[]
  publishing?: boolean
}>(), { publishing: false })

const emit = defineEmits<{
  close: []
  publish: [payload: { change_note: string; access: 'public' | 'protected' }]
  history: []
  api: []
  run: []
}>()

const access = ref<'public' | 'protected'>('public')
const changeNote = ref('')
const latest = computed(() => props.versions[0] || null)

watch(() => props.open, (open) => {
  if (!open) return
  access.value = props.workflow?.published_access === 'protected' ? 'protected' : 'public'
  changeNote.value = ''
})

function submit() {
  emit('publish', {
    access: access.value,
    change_note: changeNote.value.trim() || (props.workflow?.published_version_id ? 'Published update' : 'Initial publish'),
  })
}
</script>

<template>
  <div v-if="open" class="surface absolute right-0 top-10 z-[70] w-[360px] overflow-hidden rounded-xl shadow-2xl">
    <header class="flex items-center gap-3 border-b border-[var(--border)] px-4 py-3">
      <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><Rocket :size="16" /></span>
      <div class="min-w-0 flex-1">
        <h2 class="text-sm font-semibold">{{ $t('designer.publishApp') }}</h2>
        <p class="muted mt-0.5 text-[10px]">{{ $t('designer.publishAppHint') }}</p>
      </div>
      <button type="button" class="icon-button" :aria-label="$t('common.close')" @click="emit('close')"><X :size="14" /></button>
    </header>

    <div class="p-3">
      <div v-if="latest" class="mb-3 flex items-center gap-3 rounded-lg bg-[var(--panel-subtle)] px-3 py-2.5">
        <span class="flex h-8 w-8 items-center justify-center rounded-lg bg-emerald-50 text-[11px] font-bold text-emerald-700 dark:bg-emerald-950/40 dark:text-emerald-300">v{{ latest.version }}</span>
        <span class="min-w-0 flex-1"><span class="block text-xs font-semibold">{{ $t('designer.latestPublished') }}</span><span class="muted mt-0.5 flex items-center gap-1 text-[10px]"><Clock3 :size="10" />{{ new Date(latest.created_at).toLocaleString() }}</span></span>
      </div>
      <div v-else class="mb-3 rounded-lg border border-dashed border-[var(--border)] px-3 py-3 text-xs text-[var(--muted)]">{{ $t('designer.notPublishedYet') }}</div>

      <div class="grid grid-cols-[112px_minmax(0,1fr)] gap-2">
        <Select v-model="access" class="!h-9 !text-xs" :aria-label="$t('designer.accessMode')">
          <option value="public">{{ $t('designer.publicAccess') }}</option>
          <option value="protected">{{ $t('designer.protectedAccess') }}</option>
        </Select>
        <InputText v-model="changeNote" class="!h-9 !text-xs" :placeholder="$t('designer.changeNotePlaceholder')" />
      </div>
      <p class="muted mt-2 text-[10px] leading-4">{{ access === 'protected' ? $t('designer.protectedAccessHint') : $t('designer.publicAccessHint') }}</p>
      <Button class="mt-3 w-full" :loading="publishing" @click="submit"><Rocket :size="14" />{{ workflow?.published_version_id ? $t('designer.publishUpdate') : $t('workflow.publish') }}</Button>

      <div v-if="workflow?.published_version_id" class="mt-3 grid grid-cols-2 gap-2 border-t border-[var(--border)] pt-3">
        <button type="button" class="publish-shortcut" @click="emit('run')"><Globe2 :size="15" /><span>{{ $t('designer.openPublishedApp') }}</span><ExternalLink :size="11" class="ml-auto" /></button>
        <button type="button" class="publish-shortcut" @click="emit('api')"><Braces :size="15" /><span>{{ $t('designer.apiAccess') }}</span></button>
        <button type="button" class="publish-shortcut" @click="emit('history')"><History :size="15" /><span>{{ $t('designer.versionHistory') }}</span></button>
        <div class="publish-shortcut cursor-default"><KeyRound v-if="workflow?.published_access === 'protected'" :size="15" /><FileClock v-else :size="15" /><span>{{ workflow?.published_access === 'protected' ? $t('designer.protectedAccess') : $t('designer.publicAccess') }}</span></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.publish-shortcut { display: flex; height: 38px; align-items: center; gap: 8px; border: 1px solid var(--border); border-radius: 8px; padding: 0 10px; color: var(--muted); font-size: 11px; text-align: left; }
button.publish-shortcut:hover { background: var(--panel-subtle); color: var(--text); }
</style>
