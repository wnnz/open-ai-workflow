// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import NodeActionMenu from './NodeActionMenu.vue'

describe('NodeActionMenu', () => {
  it('emits duplicate action', async () => {
    const wrapper = mount(NodeActionMenu, { global: { plugins: [i18n] } })
    const duplicate = wrapper.findAll('button').find(button => button.text().includes('重复'))
    expect(duplicate).toBeTruthy()
    await duplicate!.trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual(['duplicate'])
  })

  it('opens the node replacement action', async () => {
    const wrapper = mount(NodeActionMenu, { global: { plugins: [i18n] } })
    const change = wrapper.findAll('button').find(button => button.text().includes('更改节点'))
    expect(change).toBeTruthy()
    await change!.trigger('click')
    expect(wrapper.emitted('action')?.[0]).toEqual(['change'])
  })

  it('protects start and end nodes from structural actions', () => {
    const wrapper = mount(NodeActionMenu, { props: { protectedNode: true }, global: { plugins: [i18n] } })
    expect(wrapper.findAll('button').filter(button => button.attributes('disabled') !== undefined)).toHaveLength(3)
  })
})
