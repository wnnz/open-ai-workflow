// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import Select from './Select.vue'

const options = [
  { label: 'gpt-5.3-codex-spark', value: 'gpt-5.3-codex-spark' },
  { label: 'gpt-5.4', value: 'gpt-5.4' },
  { label: 'gpt-5.4-mini', value: 'gpt-5.4-mini' },
  { label: 'gpt-5.6-sol', value: 'gpt-5.6-sol' },
]

describe('Select', () => {
  it('keeps every option visible while emphasizing and activating the first match', async () => {
    const wrapper = mount(Select, {
      props: {
        modelValue: 'gpt-5.6-sol',
        options,
        editable: true,
        allowCustomValue: true,
        filterOptions: false,
      },
    })

    await wrapper.get('input').setValue('5.4')

    expect(wrapper.findAll('[role="option"]')).toHaveLength(options.length)
    expect(wrapper.findAll('[role="option"] strong').map((item) => item.text())).toEqual(['5.4', '5.4'])
    const input = wrapper.get('input')
    expect(input.attributes('aria-activedescendant')).toBeTruthy()
    expect(wrapper.get(`#${input.attributes('aria-activedescendant')}`).text()).toBe('gpt-5.4')
  })

  it('rejects values outside the option list when custom values are disabled', async () => {
    const wrapper = mount(Select, {
      props: {
        modelValue: 'gpt-5.4',
        options,
        editable: true,
        allowCustomValue: false,
      },
    })

    await wrapper.get('input').setValue('unknown-model')
    await wrapper.get('div.relative').trigger('focusout', { relatedTarget: null })

    expect((wrapper.get('input').element as HTMLInputElement).value).toBe('gpt-5.4')
    expect(wrapper.emitted('update:modelValue')).toBeUndefined()
  })

  it('uses the shared option panel for strict option-slot selects', async () => {
    const wrapper = mount(Select, {
      props: { modelValue: 'a' },
      slots: { default: '<option value="a">Alpha</option><option value="b">Beta</option>' },
    })

    await wrapper.get('button[role="combobox"]').trigger('click')

    expect(wrapper.findAll('[role="option"]').map((item) => item.text())).toEqual(['Alpha', 'Beta'])
    expect(wrapper.get('button[role="combobox"]').text()).toContain('Alpha')

    // Keep the hidden native element as a compatibility bridge for existing tests and form integrations.
    await wrapper.get('select').setValue('b')

    expect(wrapper.emitted('update:modelValue')?.[0]).toEqual(['b'])
    expect(wrapper.emitted('change')).toHaveLength(1)
  })
})
