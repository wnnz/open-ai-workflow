// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import VariableField from '@/components/VariableField.vue'
import WorkflowInputField from '@/components/WorkflowInputField.vue'
import InputText from '@/volt/InputText.vue'
import Select from '@/volt/Select.vue'
import Textarea from '@/volt/Textarea.vue'
import FilterDropdown from './FilterDropdown.vue'
import MarkdownComposer from './MarkdownComposer.vue'
import SearchInput from './SearchInput.vue'

const global = {
  plugins: [i18n, [PrimeVue, { unstyled: true }] as [typeof PrimeVue, { unstyled: boolean }]],
}

describe('editable control surfaces', () => {
  it('uses the shared light input background for core controls', () => {
    const input = mount(InputText, { props: { modelValue: 'text' }, global })
    const textarea = mount(Textarea, { props: { modelValue: 'text' }, global })
    const select = mount(Select, {
      props: { modelValue: 'a' },
      slots: { default: '<option value="a">Alpha</option>' },
      global,
    })
    const editableSelect = mount(Select, {
      props: { modelValue: 'a', editable: true, options: [{ label: 'Alpha', value: 'a' }] },
      global,
    })
    const variable = mount(VariableField, { props: { modelValue: '{{start.file}}', groups: [] }, global })

    expect(input.get('input').classes()).toContain('bg-[var(--input-bg)]')
    expect(textarea.get('textarea').classes()).toContain('bg-[var(--input-bg)]')
    expect(select.get('button[role="combobox"]').classes()).toContain('bg-[var(--input-bg)]')
    expect(editableSelect.get('input[role="combobox"]').classes()).toContain('bg-[var(--input-bg)]')
    expect(variable.get('input.variable-control').classes()).toContain('bg-[var(--input-bg)]')
  })

  it('keeps read-only and disabled controls visually distinct', () => {
    const input = mount(InputText, { props: { modelValue: 'locked' }, attrs: { readonly: true }, global })
    const textarea = mount(Textarea, { props: { modelValue: 'locked' }, attrs: { disabled: true }, global })
    const select = mount(Select, {
      props: { modelValue: 'a', disabled: true },
      slots: { default: '<option value="a">Alpha</option>' },
      global,
    })

    expect(input.get('input').classes()).toContain('read-only:bg-[var(--panel-subtle)]')
    expect(textarea.get('textarea').classes()).toContain('disabled:bg-[var(--panel-subtle)]')
    expect(select.get('button[role="combobox"]').classes()).toContain('disabled:bg-[var(--panel-subtle)]')
  })

  it('uses the same surface for search, file, filter, and rich-text inputs', () => {
    const search = mount(SearchInput, { props: { modelValue: '' }, global })
    const file = mount(WorkflowInputField, {
      props: { field: { name: 'file', label: 'File', type: 'file', required: true }, modelValue: null },
      global,
    })
    const filter = mount(FilterDropdown, {
      props: { modelValue: 'all', options: [{ label: 'All', value: 'all' }] },
      global,
    })
    const markdown = mount(MarkdownComposer, { props: { modelValue: '' }, global })

    expect(search.get('input').classes()).toContain('!bg-[var(--input-bg)]')
    expect(file.get('input[type="file"]').element.parentElement?.classList).toContain('bg-[var(--input-bg)]')
    expect(filter.get('button').classes()).toContain('bg-[var(--input-bg)]')
    expect(markdown.get('.markdown-composer').classes()).toContain('bg-[var(--input-bg)]')
  })
})
