<script setup lang="ts">
import { computed } from 'vue'
import { Link2, Mail, Monitor, Plus, Trash2 } from 'lucide-vue-next'
import VariableField from '@/components/VariableField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'

const props = defineProps<{ config: Record<string, any>; variableGroups: any[] }>()
const emit = defineEmits<{ connect: [handle: string]; remove: [id: string] }>()
const methods = [
  { id: 'studio', icon: Monitor },
  { id: 'link', icon: Link2 },
  { id: 'email', icon: Mail },
]
const days = computed({
  get: () => String(Math.floor(Number(props.config.timeout_minutes || 0) / 1440)),
  set: value => { props.config.timeout_minutes = Math.max(1, Number(value || 0) * 1440 + Number(hours.value) * 60) },
})
const hours = computed({
  get: () => String(Math.floor((Number(props.config.timeout_minutes || 0) % 1440) / 60)),
  set: value => { props.config.timeout_minutes = Math.max(1, Number(days.value) * 1440 + Number(value || 0) * 60) },
})

function toggleMethod(id: string) {
  const current = Array.isArray(props.config.submission_methods) ? props.config.submission_methods : []
  props.config.submission_methods = current.includes(id) ? current.filter((item: string) => item !== id) : [...current, id]
}
function addAction() {
  const actions = Array.isArray(props.config.actions) ? props.config.actions : []
  const index = actions.length + 1
  props.config.actions = [...actions, { id: `action_${index}`, label: `Action ${index}`, value: `action_${index}`, style: 'secondary' }]
}
</script>

<template>
  <section class="mt-5 space-y-5">
    <div>
      <div class="flex items-center justify-between"><div><h3 class="text-xs font-semibold">{{ $t('designer.submissionMethods') }}</h3><p class="muted mt-1 text-[11px]">{{ $t('designer.submissionMethodsHint') }}</p></div></div>
      <div class="mt-3 grid grid-cols-3 gap-2">
        <button v-for="method in methods" :key="method.id" type="button" class="flex h-16 flex-col items-center justify-center gap-1.5 rounded-lg border text-[10px] font-medium" :class="config.submission_methods?.includes(method.id) ? 'border-[var(--primary)] bg-[var(--primary-soft)] text-[var(--primary)]' : 'border-[var(--border)] hover:bg-[var(--panel-subtle)]'" @click="toggleMethod(method.id)"><component :is="method.icon" :size="16" />{{ $t(`designer.submissionMethod.${method.id}`) }}</button>
      </div>
    </div>
    <div>
      <h3 class="text-xs font-semibold">{{ $t('designer.formContent') }}</h3>
      <p class="muted mt-1 text-[11px]">{{ $t('designer.formContentHint') }}</p>
      <VariableField v-model="config.form_content" class="mt-3 font-mono" :groups="variableGroups" multiline :rows="7" :placeholder="$t('designer.formContentPlaceholder')" />
    </div>
    <div>
      <div class="flex items-center justify-between"><div><h3 class="text-xs font-semibold">{{ $t('designer.userActions') }}</h3><p class="muted mt-1 text-[11px]">{{ $t('designer.userActionsHint') }}</p></div><button class="icon-button" type="button" :title="$t('designer.addAction')" @click="addAction"><Plus :size="14" /></button></div>
      <div class="mt-3 space-y-3">
        <div v-for="action in config.actions" :key="action.id" class="rounded-lg border border-[var(--border)] bg-[var(--panel-subtle)] p-3">
          <div class="grid grid-cols-[minmax(0,1fr)_84px_30px] gap-2"><InputText v-model="action.label" class="!h-8" :placeholder="$t('designer.actionLabel')" /><Select v-model="action.style" class="!h-8 !text-xs"><option value="primary">{{ $t('designer.primaryAction') }}</option><option value="secondary">{{ $t('designer.secondaryAction') }}</option><option value="danger">{{ $t('designer.dangerAction') }}</option></Select><button class="icon-button !h-8 !w-8 text-red-600" type="button" :title="$t('common.delete')" @click="emit('remove', action.id)"><Trash2 :size="13" /></button></div>
          <div class="mt-2 grid grid-cols-2 gap-2"><label class="field-label">ID<InputText v-model="action.id" class="mt-1 !h-8 font-mono" /></label><label class="field-label">{{ $t('designer.actionValue') }}<InputText v-model="action.value" class="mt-1 !h-8 font-mono" /></label></div>
          <button type="button" class="mt-3 flex h-8 w-full items-center justify-center gap-2 rounded-md border border-dashed border-[var(--border)] text-[10px] text-[var(--muted)] hover:border-[var(--primary)] hover:text-[var(--primary)]" @click="emit('connect', `action:${action.id}`)"><Plus :size="12" />{{ $t('designer.connectActionBranch') }}</button>
        </div>
      </div>
    </div>
    <div>
      <h3 class="text-xs font-semibold">{{ $t('designer.timeoutSettings') }}</h3>
      <div class="mt-3 grid grid-cols-2 gap-3"><label class="field-label">{{ $t('designer.days') }}<InputText v-model="days" class="mt-1.5" type="number" min="0" max="365" /></label><label class="field-label">{{ $t('designer.hours') }}<InputText v-model="hours" class="mt-1.5" type="number" min="0" max="23" /></label></div>
    </div>
  </section>
</template>
