// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowNode from './WorkflowNode.vue'

function renderNode(selected = false) {
  return mount(WorkflowNode, {
    props: {
      id: 'llm-1',
      type: 'llm',
      selected,
      connectable: true,
      position: { x: 0, y: 0 },
      dimensions: { width: 206, height: 82 },
      dragging: false,
      resizing: false,
      zIndex: 0,
      events: {},
      data: { label: 'LLM', nodeType: 'llm', config: {} },
    } as any,
    global: {
      plugins: [i18n],
      stubs: {
        Handle: { template: '<div><slot /></div>' },
        NodeValidationBadge: true,
        WorkflowNodeSummary: { inheritAttrs: false, template: '<div />' },
      },
    },
  })
}

describe('WorkflowNode', () => {
  it('uses the hover border treatment while selected', () => {
    const wrapper = renderNode(true)

    expect(wrapper.get('.workflow-card').classes()).toContain('selected')
  })

  it('closes the action menu when the user clicks outside the node', async () => {
    const wrapper = renderNode()
    await wrapper.get('button[aria-label="更多"]').trigger('click')
    expect(wrapper.find('[role="menu"]').exists()).toBe(true)

    document.body.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true }))
    await wrapper.vm.$nextTick()

    expect(wrapper.find('[role="menu"]').exists()).toBe(false)
  })
})
