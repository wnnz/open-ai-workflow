// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowNodeInspector from './WorkflowNodeInspector.vue'

describe('WorkflowNodeInspector', () => {
  it('unifies settings and last-run content for every node type', async () => {
    const wrapper = mount(WorkflowNodeInspector, {
      props: {
        node: { id: 'llm-1', data: { label: '模型', description: '' } },
        nodeType: 'llm',
        tab: 'settings',
        result: { status: 'succeeded' },
      },
      slots: { settings: '<div>LLM settings</div>' },
      global: {
        plugins: [i18n],
        stubs: {
          NodeInspectorHeader: { template: '<header>模型</header>' },
          NodeRunResultPanel: { props: ['result'], template: '<div>run {{ result.status }}</div>' },
        },
      },
    })

    expect(wrapper.text()).toContain('LLM settings')
    expect(wrapper.get('aside').classes()).toEqual(expect.arrayContaining(['z-30', 'w-full', 'lg:w-[420px]']))
    expect(wrapper.findAll('[role="tab"]')).toHaveLength(2)
    await wrapper.findAll('[role="tab"]')[1]!.trigger('click')
    expect(wrapper.emitted('update:tab')).toEqual([['run']])
    await wrapper.setProps({ tab: 'run' })
    expect(wrapper.text()).toContain('run succeeded')
  })

  it('keeps note nodes in a single settings surface', () => {
    const wrapper = mount(WorkflowNodeInspector, {
      props: { node: { id: 'note-1', data: {} }, nodeType: 'note', tab: 'settings' },
      slots: { settings: '<div>Note editor</div>' },
      global: {
        plugins: [i18n],
        stubs: {
          NodeInspectorHeader: { props: ['node', 'nodeType', 'running'], template: '<header />' },
          NodeRunResultPanel: true,
        },
      },
    })

    expect(wrapper.find('[role="tablist"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('Note editor')
  })
})
