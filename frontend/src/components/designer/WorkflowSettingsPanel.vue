<script setup lang="ts">
import { computed } from 'vue'
import { ExternalLink, Link2, Save } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import AlertBanner from '@/components/ui/AlertBanner.vue'
import FormField from '@/components/ui/FormField.vue'
import Button from '@/volt/Button.vue'
import InputText from '@/volt/InputText.vue'

const props = withDefaults(defineProps<{
  modelValue: string
  savedSlug: string
  origin: string
  published?: boolean
  saving?: boolean
  error?: string
}>(), { published: false, saving: false, error: '' })

const emit = defineEmits<{
  'update:modelValue': [value: string]
  edit: []
  save: []
}>()

const { t } = useI18n()
const slugPattern = /^[a-z0-9]+(?:-[a-z0-9]+)*$/
const slug = computed(() => props.modelValue.trim())
const publicUrl = computed(() => `${props.origin.replace(/\/$/, '')}/apps/${slug.value}`)
const dirty = computed(() => props.modelValue !== props.savedSlug)
const slugError = computed(() => {
  if (!slug.value) return t('designer.workflowSlugRequired')
  if (slug.value.length > 80) return t('designer.workflowSlugTooLong')
  if (!slugPattern.test(slug.value)) return t('designer.workflowSlugInvalid')
  return ''
})
const canSave = computed(() => dirty.value && !slugError.value && !props.saving)

function updateSlug(value: string) {
  emit('update:modelValue', value.toLowerCase())
  emit('edit')
}

function submit() {
  if (canSave.value) emit('save')
}
</script>

<template>
  <section class="surface rounded-lg">
    <header class="flex items-center gap-3 border-b border-[var(--border)] px-5 py-4">
      <span class="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><Link2 :size="17" /></span>
      <div class="min-w-0 flex-1">
        <h2 class="text-sm font-semibold">{{ t('designer.workflowPublicUrl') }}</h2>
        <p class="muted mt-0.5 text-xs">{{ t('designer.workflowSlugHint') }}</p>
      </div>
    </header>

    <form class="p-5" @submit.prevent="submit">
      <FormField :label="t('designer.workflowSlug')" :error="slugError" required>
        <InputText
          :model-value="modelValue"
          class="font-mono"
          maxlength="80"
          autocomplete="off"
          autocapitalize="none"
          spellcheck="false"
          placeholder="english-exam-answer-filler"
          @update:model-value="updateSlug"
        />
      </FormField>
      <div class="mt-3 flex min-w-0 items-center gap-2 rounded-lg bg-[var(--panel-subtle)] px-3 py-2.5 text-xs">
        <Link2 :size="14" class="shrink-0 text-[var(--primary)]" />
        <code class="min-w-0 flex-1 break-all">{{ publicUrl }}</code>
        <a
          v-if="published && !dirty && !error"
          class="icon-button shrink-0"
          :href="publicUrl"
          target="_blank"
          rel="noopener noreferrer"
          :title="t('designer.openPublishedApp')"
          :aria-label="t('designer.openPublishedApp')"
        ><ExternalLink :size="14" /></a>
      </div>
      <p v-if="published" class="mt-3 text-xs leading-5 text-amber-700 dark:text-amber-300">{{ t('designer.workflowSlugPublishedWarning') }}</p>

      <AlertBanner :message="error" tone="error" />
      <div class="mt-5 flex justify-end">
        <Button type="submit" :loading="saving" :disabled="!canSave"><Save :size="15" />{{ t('designer.saveWorkflowSettings') }}</Button>
      </div>
    </form>
  </section>
</template>
