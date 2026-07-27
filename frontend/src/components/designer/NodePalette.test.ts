// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { Bot, Code2 } from 'lucide-vue-next'
import { i18n } from '@/i18n'
import NodePalette from './NodePalette.vue'

const sections = [
  { key: 'ai', items: [{ type: 'llm', icon: Bot }] },
  { key: 'tools', items: [{ type: 'code', icon: Code2 }] },
]

describe('NodePalette', () => {
  it('selects visible nodes with arrow keys and Enter', async () => {
    const wrapper = mount(NodePalette, { props: { query: '', activeTab: 'nodes', sections, scripts: [] }, global: { plugins: [i18n] } })
    const input = wrapper.get('input')
    await input.trigger('keydown', { key: 'Enter' })
    expect(wrapper.emitted('add')?.[0]).toEqual(['llm'])
  })

  it('closes with Escape', async () => {
    const wrapper = mount(NodePalette, { props: { query: '', activeTab: 'nodes', sections, scripts: [] }, global: { plugins: [i18n] } })
    await wrapper.get('input').trigger('keydown', { key: 'Escape' })
    expect(wrapper.emitted('close')).toHaveLength(1)
  })
})
