<script setup lang="ts">
import { Plus, X } from 'lucide-vue-next'
import { useI18n } from 'vue-i18n'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import VariableField from '@/components/VariableField.vue'
import FormField from '@/components/ui/FormField.vue'
import IconButton from '@/volt/IconButton.vue'
import InputText from '@/volt/InputText.vue'
import Textarea from '@/volt/Textarea.vue'
import BranchButton from './BranchButton.vue'
import NodeConfigSection from './NodeConfigSection.vue'
import NodeSettingCard from './NodeSettingCard.vue'

defineProps<{ config: any; variableGroups: WorkflowVariableGroup[] }>()
const emit = defineEmits<{ add: []; remove: [index: number]; connect: [handle: string]; 'update-keywords': [category: any, value: string] }>()
const { t } = useI18n()
function keywords(category: any) { return Array.isArray(category.keywords) ? category.keywords.join(', ') : String(category.keywords || '') }
</script>

<template>
  <div class="mt-5">
    <NodeConfigSection :title="t('designer.nodeParameters')" :hint="t('designer.nodeParametersHint')" kind="parameters">
      <NodeConfigSection :title="t('designer.categories')" :hint="t('designer.classifierCategoriesHint')" :count="config.categories.length">
        <template #actions><IconButton :label="t('designer.addCategory')" size="sm" @click="emit('add')"><Plus :size="14" /></IconButton></template>
        <div class="space-y-3">
          <NodeSettingCard v-for="(category, index) in config.categories" :key="category.id">
            <div class="flex items-center gap-2"><span class="flex h-7 w-7 shrink-0 items-center justify-center rounded-md bg-orange-100 text-[10px] font-bold text-orange-700 dark:bg-orange-950/40 dark:text-orange-300">{{ Number(index) + 1 }}</span><InputText v-model="category.name" class="min-w-0 flex-1" :placeholder="t('designer.categoryName')" /><IconButton :label="t('common.delete')" tone="danger" size="sm" :disabled="config.categories.length <= 2" @click="emit('remove', Number(index))"><X :size="14" /></IconButton></div>
            <Textarea v-model="category.description" class="mt-2 h-16" :placeholder="t('designer.categoryDescription')" />
            <FormField class="mt-2" :label="t('designer.categoryKeywords')" compact><InputText :model-value="keywords(category)" :placeholder="t('designer.categoryKeywordsPlaceholder')" @update:model-value="emit('update-keywords', category, $event)" /></FormField>
            <BranchButton class="mt-2" :label="`${t('designer.categoryBranch')} · ${category.name || `${t('designer.categoryName')} ${Number(index) + 1}`}`" @click="emit('connect', `category:${category.id}`)" />
          </NodeSettingCard>
        </div>
      </NodeConfigSection>
    </NodeConfigSection>
    <NodeConfigSection class="mt-5 border-t border-[var(--border)] pt-5" :title="t('designer.inputVariables')" :hint="t('designer.inputVariablesHint')" :count="1" kind="input" collapsible><NodeSettingCard :title="t('designer.classifierInput')" type="String" required><VariableField v-model="config.input" class="font-mono" :groups="variableGroups" :placeholder="t('designer.variableReferencePlaceholder')" /></NodeSettingCard></NodeConfigSection>
  </div>
</template>
