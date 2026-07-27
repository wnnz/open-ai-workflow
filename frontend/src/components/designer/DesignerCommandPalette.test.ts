// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import DesignerCommandPalette from './DesignerCommandPalette.vue'

describe('DesignerCommandPalette', () => {
  it('searches existing nodes and emits focus', async () => {
    const wrapper = mount(DesignerCommandPalette, { attachTo: document.body, props: { open: true, nodes: [{ id: 'node-1', data: { label: '文档处理', description: '读取 PDF' } }], addItems: [], actions: [] }, global: { plugins: [i18n], stubs: { teleport: true } } })
    await wrapper.get('input').setValue('文档')
    expect(wrapper.text()).toContain('文档处理')
    await wrapper.get('[role="option"]').trigger('click')
    expect(wrapper.emitted('focus')?.[0]).toEqual(['node-1'])
    wrapper.unmount()
  })

  it('uses slash mode for commands', async () => {
    const wrapper = mount(DesignerCommandPalette, { props: { open: true, nodes: [], addItems: [{ type: 'llm', label: 'LLM' }], actions: [{ id: 'save', label: '保存工作流', shortcut: 'Ctrl S' }] }, global: { plugins: [i18n], stubs: { teleport: true } } })
    await wrapper.get('input').setValue('/保存')
    expect(wrapper.text()).toContain('保存工作流')
    expect(wrapper.text()).not.toContain('LLM')
  })
})
