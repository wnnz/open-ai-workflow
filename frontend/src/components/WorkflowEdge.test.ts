// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { Position } from '@vue-flow/core'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowEdge from './WorkflowEdge.vue'

const baseProps = {
  id: 'edge-1',
  source: 'source',
  target: 'target',
  sourceNode: { id: 'source', selected: false },
  targetNode: { id: 'target', selected: false },
  type: 'workflow',
  sourceX: 0,
  sourceY: 0,
  targetX: 200,
  targetY: 0,
  sourcePosition: Position.Right,
  targetPosition: Position.Left,
  sourceHandleId: undefined,
  targetHandleId: undefined,
  markerStart: '',
  markerEnd: '',
  data: {},
  events: {},
}

function render(props: Record<string, any>) {
  return mount(WorkflowEdge, {
    props: { ...baseProps, ...props } as any,
    global: {
      plugins: [i18n],
      stubs: {
        BaseEdge: { inheritAttrs: false, template: '<div data-testid="edge" :class="$attrs.class" :data-path="$attrs.path" />' },
        EdgeLabelRenderer: { template: '<div><slot /></div>' },
      },
    },
  })
}

describe('WorkflowEdge', () => {
  it('highlights edges connected to the selected node', () => {
    const wrapper = render({ sourceNode: { id: 'source', selected: true } })
    expect(wrapper.get('[data-testid="edge"]').classes()).toContain('connected')
    expect(wrapper.find('.workflow-edge-actions').classes()).toContain('connected')
  })

  it('keeps unrelated edges neutral', () => {
    const wrapper = render({})
    expect(wrapper.get('[data-testid="edge"]').classes()).not.toContain('connected')
  })

  it('renders a bezier curve between nodes', () => {
    const wrapper = render({ targetY: 120 })
    expect(wrapper.get('[data-testid="edge"]').attributes('data-path')).toMatch(/^M.*C/)
  })
})
