// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import NodeSettingCard from './NodeSettingCard.vue'

describe('NodeSettingCard', () => {
  it('renders the shared label, type, hint, action, and control layout', () => {
    const wrapper = mount(NodeSettingCard, {
      props: { title: '上下文', hint: '绑定上游变量', type: 'String', required: true, divided: true },
      slots: { default: '<input data-testid="control">', actions: '<button data-testid="action">toggle</button>' },
    })

    expect(wrapper.text()).toContain('上下文')
    expect(wrapper.text()).toContain('String')
    expect(wrapper.text()).toContain('绑定上游变量')
    expect(wrapper.find('[data-testid="control"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="action"]').exists()).toBe(true)
    expect(wrapper.get('[data-testid="control"]').element.parentElement?.classList).toContain('border-t')
  })
})
