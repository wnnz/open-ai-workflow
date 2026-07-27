// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import SelectionToolbar from './SelectionToolbar.vue'

describe('SelectionToolbar', () => {
  it('shows the selected count and emits batch actions', async () => {
    const wrapper = mount(SelectionToolbar, { props: { count: 3 }, global: { plugins: [i18n] } })
    expect(wrapper.text()).toContain('已选择 3 个节点')
    const buttons = wrapper.findAll('button')
    await buttons[1].trigger('click')
    await buttons[2].trigger('click')
    expect(wrapper.emitted('duplicate')).toHaveLength(1)
    expect(wrapper.emitted('delete')).toHaveLength(1)
  })
})
