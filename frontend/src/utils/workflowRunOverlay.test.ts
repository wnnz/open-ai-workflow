import { describe, expect, it } from 'vitest'
import { buildRunOverlay, clearRunOverlay, stripRuntimeData } from './workflowRunOverlay'

describe('workflow run overlay', () => {
  const nodes = [
    { id: 'start', type: 'start', data: { nodeType: 'start' } },
    { id: 'condition', type: 'condition', data: { nodeType: 'condition' } },
    { id: 'yes', type: 'template', data: { nodeType: 'template' } },
    { id: 'no', type: 'template', data: { nodeType: 'template' } },
  ]
  const edges = [
    { id: 'a', source: 'start', target: 'condition', data: {} },
    { id: 'b', source: 'condition', target: 'yes', data: {} },
    { id: 'c', source: 'condition', target: 'no', data: {} },
  ]

  it('marks executed nodes and edges while dimming the skipped branch', () => {
    const overlay = buildRunOverlay(nodes, edges, { id: 'run-1', triggered_by: 'studio', trace: [
      { node_id: 'start', status: 'succeeded', started_at: '2026-01-01T00:00:00.000Z', finished_at: '2026-01-01T00:00:00.010Z' },
      { node_id: 'condition', status: 'succeeded' },
      { node_id: 'yes', status: 'succeeded' },
    ] })
    expect(overlay.nodes.find(node => node.id === 'start')?.data.runtimeDurationMs).toBe(10)
    expect(overlay.nodes.find(node => node.id === 'no')?.data.runtimeStatus).toBe('skipped')
    expect(overlay.edges.find(edge => edge.id === 'b')?.data.runtimeStatus).toBe('active')
    expect(overlay.edges.find(edge => edge.id === 'c')?.data.runtimeStatus).toBe('skipped')
  })

  it('keeps runtime fields out of persisted data and can clear the overlay', () => {
    expect(stripRuntimeData({ label: 'Node', runtimeStatus: 'succeeded', runtimeRunId: 'run-1', validationMessages: ['Invalid'] })).toEqual({ label: 'Node' })
    const validationNodes = nodes.map(node => node.id === 'start' ? { ...node, data: { ...node.data, validationMessages: ['Invalid'] } } : node)
    const overlay = buildRunOverlay(validationNodes, edges, { id: 'run-1', triggered_by: 'studio', trace: [{ node_id: 'start' }] })
    expect(overlay.nodes.find(node => node.id === 'start')?.data.validationMessages).toEqual(['Invalid'])
    const cleared = clearRunOverlay(overlay.nodes, overlay.edges)
    expect(cleared.nodes.every(node => !('runtimeStatus' in node.data))).toBe(true)
    expect(cleared.nodes.find(node => node.id === 'start')?.data.validationMessages).toEqual(['Invalid'])
    expect(cleared.edges.every(edge => !('runtimeStatus' in edge.data))).toBe(true)
  })
})
