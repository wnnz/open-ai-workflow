// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowCanvasControls from './WorkflowCanvasControls.vue'

describe('WorkflowCanvasControls', () => {
  it('exposes the canvas modes and editing actions through a reusable contract', async () => {
    const wrapper = mount(WorkflowCanvasControls, {
      props: {
        interactionMode: 'pointer',
        annotationActive: true,
        commentsActive: false,
        canCopy: true,
        canPaste: true,
        canDelete: true,
        canUndo: true,
        canRedo: false,
        zoomPercent: 80,
      },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('80%')
    await wrapper.get('[data-testid="open-node-palette"]').trigger('click')
    await wrapper.get('button[title="手模式"]').trigger('click')
    await wrapper.get('button[title="更多编辑操作"]').trigger('click')
    await wrapper.findAll('button').find(button => button.text().includes('复制节点'))!.trigger('click')

    expect(wrapper.emitted('addNode')).toHaveLength(1)
    expect(wrapper.emitted('update:interactionMode')).toEqual([['hand']])
    expect(wrapper.emitted('copy')).toHaveLength(1)
    expect(wrapper.get('button[title="重做"]').attributes('disabled')).toBeDefined()
  })
})
