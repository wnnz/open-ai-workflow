<script setup lang="ts">
import { computed } from 'vue'
import { ExternalLink, Link2, Save, Settings2 } from 'lucide-vue-next'
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
  <section class="min-h-0 flex-1 overflow-auto p-7">
    <div class="mx-auto max-w-3xl">
      <header class="flex items-start gap-3">
        <span class="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-[var(--primary-soft)] text-[var(--primary)]"><Settings2 :size="19" /></span>
        <div>
          <h2 class="text-xl font-semibold">{{ t('designer.workflowSettings') }}</h2>
          <p class="muted mt-1 text-sm">{{ t('designer.workflowSettingsHint') }}</p>
        </div>
      </header>

      <form class="mt-7" @submit.prevent="submit">
        <div class="grid gap-5 border-y border-[var(--border)] py-6 sm:grid-cols-[190px_minmax(0,1fr)]">
          <div>
            <h3 class="text-sm font-semibold">{{ t('designer.workflowPublicUrl') }}</h3>
            <p class="muted mt-1 text-xs leading-5">{{ t('designer.workflowSlugHint') }}</p>
          </div>
          <div class="min-w-0">
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
          </div>
        </div>

        <AlertBanner :message="error" tone="error" />
        <div class="mt-5 flex justify-end">
          <Button type="submit" :loading="saving" :disabled="!canSave"><Save :size="15" />{{ t('designer.saveWorkflowSettings') }}</Button>
        </div>
      </form>
    </div>
  </section>
</template>
