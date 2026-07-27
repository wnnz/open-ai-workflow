// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import NodeValidationBadge from './NodeValidationBadge.vue'

describe('NodeValidationBadge', () => {
  it('summarizes messages and focuses the invalid node', async () => {
    const wrapper = mount(NodeValidationBadge, { props: { messages: ['请选择模型', '请填写提示词'] }, global: { plugins: [i18n] } })
    expect(wrapper.get('button').attributes('title')).toContain('请选择模型')
    expect(wrapper.get('button').text()).toContain('2')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('focus')).toHaveLength(1)
  })

  it('stays hidden when the node is valid', () => {
    const wrapper = mount(NodeValidationBadge, { props: { messages: [] }, global: { plugins: [i18n] } })
    expect(wrapper.find('button').exists()).toBe(false)
  })
})
