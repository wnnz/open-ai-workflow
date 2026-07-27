// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import VariableField from './VariableField.vue'

describe('VariableField', () => {
  it('opens suggestions after typing mustache and replaces the active token', async () => {
    const wrapper = mount(VariableField, {
      props: {
        modelValue: '',
        groups: [{ nodeId: 'llm-1', label: '大模型1', variables: [{ path: '大模型1.text', label: 'text', type: 'String' }] }],
        'onUpdate:modelValue': value => wrapper.setProps({ modelValue: value }),
      },
      global: { plugins: [i18n] },
    })
    const input = wrapper.get('input.variable-control')
    await input.setValue('前缀 {{大')
    expect(wrapper.find('.variable-popover').exists()).toBe(true)
    expect(wrapper.get('.variable-popover').attributes('style')).not.toContain('calc(100%')
    expect(wrapper.text()).toContain('大模型1.text')

    await wrapper.get('.variable-option').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['前缀 {{大模型1.text}}'])
  })

  it('supports mustache suggestions in multiline runtime fields', async () => {
    const wrapper = mount(VariableField, {
      props: {
        modelValue: '',
        multiline: true,
        groups: [{ nodeId: 'start-1', label: '开始', variables: [{ path: '开始.message', label: 'message', type: 'String' }] }],
        'onUpdate:modelValue': value => wrapper.setProps({ modelValue: value }),
      },
      global: { plugins: [i18n] },
    })
    const textarea = wrapper.get('textarea.variable-control')
    await textarea.setValue('正文 {{开')
    expect(wrapper.find('.variable-popover').exists()).toBe(true)
    expect(wrapper.get('.variable-popover').attributes('style')).not.toContain('calc(100%')

    await wrapper.get('.variable-option').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['正文 {{开始.message}}'])
  })
})
