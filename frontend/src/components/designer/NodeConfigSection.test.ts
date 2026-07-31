// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import NodeConfigSection from './NodeConfigSection.vue'

describe('NodeConfigSection', () => {
  it('supports a collapsed section with a count badge', async () => {
    const wrapper = mount(NodeConfigSection, {
      props: { title: '输出变量', count: 3, collapsible: true, defaultExpanded: false, kind: 'output' },
      slots: { icon: '<span data-testid="icon">icon</span>', default: '<div data-testid="content">content</div>' },
      global: { plugins: [i18n] },
    })
    expect(wrapper.text()).toContain('3')
    expect(wrapper.attributes('data-section-kind')).toBe('output')
    expect(wrapper.find('[data-testid="icon"]').exists()).toBe(true)
    expect(wrapper.find('[data-testid="content"]').exists()).toBe(false)
    await wrapper.get('button[aria-expanded="false"]').trigger('click')
    expect(wrapper.find('[data-testid="content"]').exists()).toBe(true)
    expect(wrapper.emitted('toggle')).toEqual([[true]])
  })
})
