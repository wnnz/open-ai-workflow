<script setup lang="ts">
import FormField from '@/components/ui/FormField.vue'
import VariableField from '@/components/VariableField.vue'
import type { WorkflowVariableGroup } from '@/utils/workflowVariables'
import Textarea from '@/volt/Textarea.vue'
withDefaults(defineProps<{ modelValue: string; label: string; error?: string; heightClass?: string; groups?: WorkflowVariableGroup[] }>(), { error: '', heightClass: 'h-36', groups: undefined })
const emit = defineEmits<{ 'update:modelValue': [value: string]; input: []; focus: [event: FocusEvent]; blur: [event: FocusEvent] }>()
function update(value: string) { emit('update:modelValue', value); emit('input') }
</script>

<template>
  <FormField :label="label" :error="error" compact>
    <VariableField v-if="groups" :model-value="modelValue" :groups="groups" multiline :control-class="`${heightClass} font-mono !text-xs`" @update:model-value="update" @focus="emit('focus', $event)" @blur="emit('blur', $event)" />
    <Textarea v-else :model-value="modelValue" class="font-mono !text-xs" :class="heightClass" spellcheck="false" @update:model-value="update" @focus="emit('focus', $event)" @blur="emit('blur', $event)" />
  </FormField>
</template>
