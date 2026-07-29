// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowInputField from './WorkflowInputField.vue'

describe('WorkflowInputField', () => {
  it('omits the select placeholder option when no placeholder is configured', async () => {
    const wrapper = mount(WorkflowInputField, {
      props: {
        field: {
          name: 'resolution',
          label: 'Resolution',
          type: 'select',
          required: true,
          placeholder: '',
          options: ['1024x1024', '2048x2048'],
        },
        modelValue: '1024x1024',
      },
      global: { plugins: [i18n] },
    })

    expect(wrapper.findAll('option').map(option => option.text())).toEqual(['1024x1024', '2048x2048'])

    await wrapper.get('button[role="combobox"]').trigger('click')
    expect(wrapper.findAll('[role="option"]').map(option => option.text())).toEqual(['1024x1024', '2048x2048'])
  })
})
