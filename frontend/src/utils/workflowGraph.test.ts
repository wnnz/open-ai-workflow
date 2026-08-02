import { describe, expect, it } from 'vitest'
import { absoluteNodePosition, clearWorkflowEdgeSelection, containerEntryPoints, containerSizeForChildren, findAvailableNodePosition, insertNodeOnEdge, isConnectionAllowed, layoutContainerChildren, layoutWorkflow, mergeWorkflowEdges, nextContainerChildPosition, removeWorkflowEdgeById, replaceWorkflowNode, validateWorkflowGraph, type WorkflowEdgeLike } from './workflowGraph'

const nodes = [
  { id: 'start', type: 'start', position: { x: 0, y: 0 }, data: { nodeType: 'start' } },
  { id: 'task', type: 'llm', position: { x: 0, y: 0 }, data: { nodeType: 'llm' } },
  { id: 'end', type: 'end', position: { x: 0, y: 0 }, data: { nodeType: 'end', config: { outputs: [{ name: 'result', type: 'String', value: '{{task.text}}' }] } } },
]

describe('workflow graph utilities', () => {
  it('merges partial edge stores without dropping unrelated connections', () => {
    const pending: WorkflowEdgeLike[] = [
      { id: 'edge-1', source: 'start', target: 'task' },
      { id: 'edge-2', source: 'task', target: 'end' },
    ]
    const runtime: WorkflowEdgeLike[] = [{ id: 'edge-2', source: 'task', target: 'end', data: { selected: true } }]
    const merged = mergeWorkflowEdges(pending, runtime)

    expect(merged).toHaveLength(2)
    expect(merged.find(edge => edge.id === 'edge-2')?.data).toEqual({ selected: true })
    expect(merged.filter(edge => edge.id !== 'edge-1')).toHaveLength(1)
  })

  it('keeps deselection and deletion as separate edge operations', () => {
    const existing = [
      { id: 'edge-1', source: 'start', target: 'task', selected: true },
      { id: 'edge-2', source: 'task', target: 'end', selected: false },
    ]

    const deselected = clearWorkflowEdgeSelection(existing)
    expect(deselected).toHaveLength(2)
    expect(deselected.every(edge => edge.selected === false)).toBe(true)
    expect(removeWorkflowEdgeById(deselected, 'edge-1')).toEqual([deselected[1]])
  })

  it('places newly added nodes in the nearest open lane', () => {
    const occupied = [
      { id: 'start', type: 'start', position: { x: 80, y: 160 } },
      { id: 'end', type: 'end', position: { x: 420, y: 160 } },
    ]

    expect(findAvailableNodePosition(occupied, { x: 350, y: 160 }, { ignoreIds: ['start'] })).toEqual({ x: 350, y: 280 })
    expect(findAvailableNodePosition(occupied, { x: 690, y: 160 })).toEqual({ x: 690, y: 160 })
  })

  it('only avoids collisions inside the same container', () => {
    const child = { id: 'child', type: 'template', parentNode: 'iteration', position: { x: 230, y: 84 } }
    expect(findAvailableNodePosition([child], { x: 230, y: 84 })).toEqual({ x: 230, y: 84 })
    expect(findAvailableNodePosition([child], { x: 230, y: 84 }, { parentNode: 'iteration' })).toEqual({ x: 230, y: 204 })
  })

  it('positions container children compactly and keeps padded bounds', () => {
    const container = { id: 'iteration', type: 'iteration', position: { x: 400, y: 160 }, style: { width: '800px', height: '700px' } }
    const first = { id: 'first', type: 'template', parentNode: 'iteration', position: { x: 230, y: 84 }, dimensions: { width: 206, height: 82 } }
    const second = { id: 'second', type: 'template', parentNode: 'iteration', position: { x: 230, y: 184 }, dimensions: { width: 206, height: 96 } }
    const graphNodes = [container, first, second]

    expect(nextContainerChildPosition(graphNodes, 'iteration')).toEqual({ x: 230, y: 298 })
    expect(containerSizeForChildren(graphNodes, 'iteration')).toEqual({ width: 520, height: 316 })
    expect(absoluteNodePosition(graphNodes, 'second')).toEqual({ x: 630, y: 344 })
  })

  it('allows a container to shrink again after a child moves inward', () => {
    const container = { id: 'iteration', type: 'iteration', position: { x: 0, y: 0 }, style: { width: '900px', height: '900px' } }
    const child = { id: 'child', type: 'template', parentNode: 'iteration', position: { x: 620, y: 600 }, dimensions: { width: 206, height: 82 } }
    expect(containerSizeForChildren([container, child], 'iteration')).toEqual({ width: 862, height: 718 })

    child.position = { x: 230, y: 84 }
    expect(containerSizeForChildren([container, child], 'iteration')).toEqual({ width: 520, height: 260 })
  })

  it('connects the visual container start to every child entry node', () => {
    const children = [
      { id: 'first', type: 'template', parentNode: 'iteration', position: { x: 230, y: 84 }, dimensions: { height: 82 } },
      { id: 'second', type: 'template', parentNode: 'iteration', position: { x: 230, y: 184 }, dimensions: { height: 96 } },
      { id: 'parallel', type: 'template', parentNode: 'iteration', position: { x: 230, y: 300 }, dimensions: { height: 82 } },
    ]
    const entries = containerEntryPoints(children, [{ source: 'first', target: 'second' }], 'iteration')

    expect(entries).toEqual([
      { nodeId: 'first', x: 230, y: 125 },
      { nodeId: 'parallel', x: 230, y: 341 },
    ])
  })

  it('rejects duplicate, reversed terminal, self, and cyclic connections', () => {
    const edges = [{ id: 'a', source: 'start', target: 'task' }, { id: 'legacy-duplicate', source: 'start', target: 'task' }]
    expect(isConnectionAllowed(nodes, edges, { source: 'start', target: 'task' })).toBe(false)
    expect(isConnectionAllowed(nodes, edges, { id: 'a', source: 'start', target: 'task' })).toBe(true)
    expect(isConnectionAllowed(nodes, edges, { source: 'end', target: 'task' })).toBe(false)
    expect(isConnectionAllowed(nodes, edges, { source: 'task', target: 'start' })).toBe(false)
    expect(isConnectionAllowed(nodes, edges, { source: 'task', target: 'task' })).toBe(false)
    expect(isConnectionAllowed(nodes, edges, { source: 'task', target: 'end' })).toBe(true)
    expect(isConnectionAllowed(nodes, [...edges, { id: 'b', source: 'task', target: 'end' }], { source: 'end', target: 'start' })).toBe(false)
  })

  it('allows separate classifier branches to converge on the same target', () => {
    const classifierNodes = [
      ...nodes,
      { id: 'classifier', type: 'classifier', position: { x: 100, y: 100 } },
    ]
    const classifierEdges = [
      { id: 'sales', source: 'classifier', sourceHandle: 'category:sales', target: 'task' },
    ]

    expect(isConnectionAllowed(classifierNodes, classifierEdges, {
      source: 'classifier', sourceHandle: 'category:support', target: 'task',
    })).toBe(true)
    expect(isConnectionAllowed(classifierNodes, classifierEdges, {
      source: 'classifier', sourceHandle: 'category:sales', target: 'task',
    })).toBe(false)
  })

  it('lays a workflow out from left to right by dependency level', () => {
    const laidOut = layoutWorkflow(nodes, [
      { id: 'a', source: 'start', target: 'task' },
      { id: 'b', source: 'task', target: 'end' },
    ])
    expect(laidOut.find(node => node.id === 'start')!.position.x).toBeLessThan(laidOut.find(node => node.id === 'task')!.position.x)
    expect(laidOut.find(node => node.id === 'task')!.position.x).toBeLessThan(laidOut.find(node => node.id === 'end')!.position.x)
  })

  it('uses measured container widths so adjacent layers do not overlap', () => {
    const large = { id: 'large', type: 'iteration', position: { x: 0, y: 0 }, style: { width: '720px', height: '420px' } }
    const next = { id: 'next', type: 'template', position: { x: 0, y: 0 }, dimensions: { width: 206, height: 82 } }
    const laidOut = layoutWorkflow([large, next], [{ source: 'large', target: 'next' }])
    const largePosition = laidOut.find(node => node.id === 'large')!.position
    const nextPosition = laidOut.find(node => node.id === 'next')!.position
    expect(nextPosition.x).toBeGreaterThanOrEqual(largePosition.x + 720 + 80)
  })

  it('reorders nodes within dependency layers to reduce crossing edges', () => {
    const graphNodes = [
      { id: 'top-left', type: 'template', position: { x: 0, y: 100 } },
      { id: 'bottom-left', type: 'template', position: { x: 0, y: 300 } },
      { id: 'top-right', type: 'template', position: { x: 300, y: 100 } },
      { id: 'bottom-right', type: 'template', position: { x: 300, y: 300 } },
    ]
    const laidOut = layoutWorkflow(graphNodes, [
      { source: 'top-left', target: 'bottom-right' },
      { source: 'bottom-left', target: 'top-right' },
    ])

    expect(laidOut.find(node => node.id === 'bottom-right')!.position.y).toBeLessThan(laidOut.find(node => node.id === 'top-right')!.position.y)
  })

  it('uses resized container styles instead of stale measured dimensions', () => {
    const iteration = { id: 'iteration', type: 'iteration', position: { x: 0, y: 0 }, dimensions: { width: 900, height: 900 }, style: { width: '520px', height: '260px' } }
    const sibling = { id: 'sibling', type: 'template', position: { x: 0, y: 0 }, dimensions: { width: 206, height: 82 } }
    const end = { id: 'end', type: 'end', position: { x: 0, y: 0 }, dimensions: { width: 206, height: 82 } }
    const laidOut = layoutWorkflow([iteration, sibling, end], [
      { source: 'iteration', target: 'end' },
      { source: 'sibling', target: 'end' },
    ])

    expect(laidOut.find(node => node.id === 'sibling')!.position.y).toBeLessThan(500)
    expect(laidOut.find(node => node.id === 'end')!.position.x).toBeGreaterThanOrEqual(700)
  })

  it('stacks disconnected same-level container children in one column', () => {
    const children = [
      { id: 'third', type: 'template', position: { x: 600, y: 300 }, dimensions: { width: 206, height: 96 } },
      { id: 'first', type: 'template', position: { x: 100, y: 100 }, dimensions: { width: 206, height: 82 } },
      { id: 'second', type: 'template', position: { x: 300, y: 100 }, dimensions: { width: 206, height: 82 } },
    ]
    const laidOut = layoutContainerChildren(children, [])

    expect(laidOut.map(node => node.position.x)).toEqual([230, 230, 230])
    expect(laidOut.map(node => node.id)).toEqual(['first', 'second', 'third'])
    expect(laidOut.map(node => node.position.y)).toEqual([84, 184, 284])
  })

  it('uses start, regular nodes, and end order for an unconnected draft', () => {
    const laidOut = layoutWorkflow(nodes, [])
    expect(laidOut.find(node => node.id === 'start')!.position.x).toBeLessThan(laidOut.find(node => node.id === 'task')!.position.x)
    expect(laidOut.find(node => node.id === 'task')!.position.x).toBeLessThan(laidOut.find(node => node.id === 'end')!.position.x)
    expect(new Set(laidOut.map(node => node.position.y))).toEqual(new Set([180]))
  })

  it('reports disconnected and incomplete node configuration', () => {
    const issues = validateWorkflowGraph([
      { ...nodes[0], data: { nodeType: 'start', label: 'Start', config: { triggers: [], input_fields: [] } } },
      { ...nodes[1], data: { nodeType: 'llm', label: 'Writer', config: { model: '' } } },
      nodes[2],
    ], [])
    expect(issues.map(issue => issue.code)).toEqual(expect.arrayContaining([
      'startTriggerRequired',
      'startNotConnected',
      'nodeNotConnected',
      'llmModelRequired',
      'endNotConnected',
    ]))
  })

  it('accepts a complete linear workflow', () => {
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['form'], input_fields: [{ name: 'message' }] } } },
      { ...nodes[1], data: { nodeType: 'llm', config: { model: 'gpt-4.1-mini', messages: [{ role: 'user', content: '{{inputs.message}}' }], temperature: 0.7, top_p: 1, max_tokens: 1024 } } },
      nodes[2],
    ]
    expect(validateWorkflowGraph(configured, [
      { id: 'a', source: 'start', target: 'task' },
      { id: 'b', source: 'task', target: 'end' },
    ])).toEqual([])
  })

  it('requires exactly one start trigger', () => {
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', label: 'Start', config: { triggers: ['form', 'api'], input_fields: [] } } },
      { ...nodes[1], data: { nodeType: 'llm', config: { model: 'gpt-4.1-mini', messages: [{ role: 'user', content: 'Hello' }], temperature: 0.7, top_p: 1, max_tokens: 1024 } } },
      nodes[2],
    ]
    const edges = [{ id: 'a', source: 'start', target: 'task' }, { id: 'b', source: 'task', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toContain('startTriggerExclusive')
  })

  it('validates advanced node requirements', () => {
    const advanced = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [] } } },
      { id: 'agent', type: 'agent', position: { x: 0, y: 0 }, data: { nodeType: 'agent', label: 'Agent', config: { model: '' } } },
      nodes[2],
    ]
    const advancedEdges = [
      { id: 'a', source: 'start', target: 'agent' },
      { id: 'b', source: 'agent', target: 'end' },
    ]
    expect(validateWorkflowGraph(advanced, advancedEdges).map(issue => issue.code)).toContain('agentModelRequired')
    ;(advanced[1] as any).data.config.model = 'gpt-4.1-mini'
    expect(validateWorkflowGraph(advanced, advancedEdges)).toEqual([])
  })

  it('validates structured end outputs', () => {
    const invalidEnd = { ...nodes[2], data: { nodeType: 'end', label: 'Output', config: { outputs: [
      { name: 'result', type: 'String', value: '' },
      { name: 'result', type: 'String', value: '{{task.text}}' },
    ] } } }
    const issues = validateWorkflowGraph([nodes[0], nodes[1], invalidEnd], [
      { id: 'a', source: 'start', target: 'task' },
      { id: 'b', source: 'task', target: 'end' },
    ])
    expect(issues.map(issue => issue.code)).toEqual(expect.arrayContaining(['duplicateOutputName', 'endOutputValueRequired']))
  })

  it('validates select input options', () => {
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', label: 'Start', config: { triggers: ['form'], input_fields: [{ name: 'tone', type: 'select', options: ['Formal', 'Formal'] }] } } },
      { ...nodes[1], data: { nodeType: 'llm', config: { model: 'gpt-4.1-mini', messages: [{ role: 'user', content: '{{inputs.message}}' }], temperature: 0.7, top_p: 1, max_tokens: 1024 } } },
      nodes[2],
    ]
    const edges = [{ id: 'a', source: 'start', target: 'task' }, { id: 'b', source: 'task', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toContain('inputSelectOptionsRequired')
    ;(configured[0] as any).data.config.input_fields[0].options = ['Formal', 'Friendly']
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('validates structured condition rules and branch handles', () => {
    const condition = { id: 'condition', type: 'condition', position: { x: 0, y: 0 }, data: { nodeType: 'condition', label: 'Route', config: { logical_operator: 'and', conditions: [{ variable: '', operator: 'equals', value: '' }] } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'message' }] } } },
      condition,
      nodes[2],
    ]
    const edges = [
      { id: 'a', source: 'start', target: 'condition' },
      { id: 'b', source: 'condition', sourceHandle: 'true', target: 'end' },
      { id: 'c', source: 'condition', sourceHandle: 'false', target: 'end' },
    ]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toContain('conditionClauseIncomplete')
    ;(condition as any).data.config.conditions[0] = { variable: '{{inputs.message}}', operator: 'equals', value: 'yes' }
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('requires a stable connected branch for every classifier category', () => {
    const classifier = { id: 'classifier', type: 'classifier', position: { x: 0, y: 0 }, data: { nodeType: 'classifier', label: 'Classify', config: { input: '{{inputs.message}}', categories: [
      { id: 'sales', name: 'Sales', description: '', keywords: ['buy'] },
      { id: 'support', name: 'Support', description: '', keywords: ['broken'] },
    ] } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'message' }] } } },
      classifier,
      nodes[2],
    ]
    const incomplete = [
      { id: 'a', source: 'start', target: 'classifier' },
      { id: 'b', source: 'classifier', sourceHandle: 'category:sales', target: 'end' },
    ]
    expect(validateWorkflowGraph(configured, incomplete).map(issue => issue.code)).toContain('classifierBranchesRequired')
    expect(validateWorkflowGraph(configured, [...incomplete, { id: 'c', source: 'classifier', sourceHandle: 'category:support', target: 'end' }])).toEqual([])
  })

  it('validates LLM prompt messages, parameters, and structured output', () => {
    const llm = { ...nodes[1], data: { nodeType: 'llm', label: 'Writer', config: { model: 'gpt-4.1-mini', messages: [{ role: 'user', content: '' }], temperature: 3, top_p: 1, max_tokens: 1024, response_format: 'json_schema', response_schema: null } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'message' }] } } },
      llm,
      nodes[2],
    ]
    const edges = [{ id: 'a', source: 'start', target: 'task' }, { id: 'b', source: 'task', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toEqual(expect.arrayContaining(['llmMessagesRequired', 'llmParametersInvalid', 'llmSchemaRequired']))
    ;(llm as any).data.config.messages[0].content = '{{inputs.message}}'
    ;(llm as any).data.config.temperature = 0.7
    ;(llm as any).data.config.response_schema = { type: 'object', properties: { title: { type: 'string' } } }
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('allows image generation without a size parameter', () => {
    const image = { id: 'image', type: 'image', position: { x: 0, y: 0 }, data: { nodeType: 'image', label: 'Generate', config: {
      provider_id: 'provider-1', model: 'gpt-image-2', prompt: '{{inputs.prompt}}', count: 1,
      quality: 'high', output_format: 'png', output_compression: 100, timeout_seconds: 600,
    } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'prompt' }] } } },
      image,
      { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'images', type: 'Array', value: '{{image.images}}' }] } } },
    ]
    const edges = [{ id: 'a', source: 'start', target: 'image' }, { id: 'b', source: 'image', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('validates HTTP URL, limits, and authentication while allowing variable URLs', () => {
    const http = { id: 'http', type: 'http', position: { x: 0, y: 0 }, data: { nodeType: 'http', label: 'Request', config: {
      method: 'POST', url: 'ftp://example.test', timeout_seconds: 0, max_response_bytes: 100,
      headers: {}, query: {}, auth: { type: 'bearer', token: '' }, body_type: 'json', body: {},
    } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'url' }] } } },
      http,
      { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'status', type: 'Number', value: '{{http.status_code}}' }] } } },
    ]
    const edges = [{ id: 'a', source: 'start', target: 'http' }, { id: 'b', source: 'http', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toEqual(expect.arrayContaining([
      'httpUrlInvalid', 'httpTimeoutInvalid', 'httpResponseLimitInvalid', 'httpAuthIncomplete',
    ]))
    Object.assign((http as any).data.config, {
      url: '{{inputs.url}}', timeout_seconds: 30, max_response_bytes: 2_000_000, auth: { type: 'none' },
    })
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('validates dedicated answer-filler inputs separately from document settings', () => {
    const document = { id: 'document', type: 'answer_filler', position: { x: 0, y: 0 }, data: { nodeType: 'answer_filler', label: 'Answer filler', config: { source: '', answers: '' } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'files', type: 'files' }] } } },
      document,
      { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'file', type: 'File', value: '{{document.file}}' }] } } },
    ]
    const edges = [{ id: 'a', source: 'start', target: 'document' }, { id: 'b', source: 'document', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toEqual(expect.arrayContaining(['answerFillerSourceRequired', 'answerFillerPlanRequired']))
    Object.assign((document as any).data.config, { source: '{{inputs.files}}', answers: '{{llm.structured_output}}' })
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('requires a normal path and a connected error branch for error handling', () => {
    const task = { id: 'task', type: 'template', position: { x: 0, y: 0 }, data: { nodeType: 'template', label: 'Transform', config: {
      template: '{{inputs.message}}', retry: { enabled: true, max_retries: 3, interval_seconds: 1 }, error_strategy: 'error_branch',
    } } }
    const errorEnd = { id: 'error-end', type: 'end', position: { x: 0, y: 0 }, data: { nodeType: 'end', config: { outputs: [{ name: 'error', value: '{{task.error_message}}' }] } } }
    const configured = [
      { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'message' }] } } },
      task,
      nodes[2],
      errorEnd,
    ]
    const normalEdges = [{ id: 'a', source: 'start', target: 'task' }, { id: 'b', source: 'task', target: 'end' }]
    expect(validateWorkflowGraph(configured, normalEdges).map(issue => issue.code)).toContain('errorBranchRequired')
    expect(validateWorkflowGraph(configured, [...normalEdges, { id: 'c', source: 'task', sourceHandle: 'error', target: 'error-end' }])).toEqual([])
  })

  it('validates template bindings and aggregation groups', () => {
    const start = { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['api'], input_fields: [{ name: 'message' }] } } }
    const template = { id: 'template', type: 'template', position: { x: 0, y: 0 }, data: { nodeType: 'template', label: 'Template', config: { template: 'Hello {{ name }}', inputs: [{ name: 'name', value: '' }, { name: 'name', value: '{{inputs.message}}' }] } } }
    const aggregate = { id: 'aggregate', type: 'aggregate', position: { x: 0, y: 0 }, data: { nodeType: 'aggregate', label: 'Aggregate', config: { group_enabled: true, groups: [{ name: 'result', variables: [] }, { name: 'result', variables: ['{{template.text}}'] }] } } }
    const end = { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'result', type: 'Any', value: '{{aggregate.result}}' }] } } }
    const configured = [start, template, aggregate, end]
    const edges = [{ id: 'a', source: 'start', target: 'template' }, { id: 'b', source: 'template', target: 'aggregate' }, { id: 'c', source: 'aggregate', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toEqual(expect.arrayContaining(['templateInputsInvalid', 'aggregateGroupsInvalid']))
    ;(template as any).data.config.inputs = [{ name: 'name', value: '{{inputs.message}}' }]
    ;(aggregate as any).data.config.groups = [{ name: 'result', variables: ['{{template.text}}'] }]
    expect(validateWorkflowGraph(configured, edges)).toEqual([])
  })

  it('validates variable assignments, parameter extraction, and list settings', () => {
    const start = { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['form'], input_fields: [{ name: 'message' }] } } }
    const variable = { id: 'variable', type: 'variable', position: { x: 0, y: 0 }, data: { nodeType: 'variable', label: 'Variables', config: { assignments: [{ name: 'bad-name', type: 'Unknown', operation: 'overwrite' }] } } }
    const extract = { id: 'extract', type: 'extract', position: { x: 0, y: 0 }, data: { nodeType: 'extract', label: 'Extract', config: { source: '{{inputs.message}}', model: '', fields: [{ name: 'name' }, { name: 'name' }] } } }
    const list = { id: 'list', type: 'list', position: { x: 0, y: 0 }, data: { nodeType: 'list', label: 'List', config: { source: '{{variable.items}}', nth: { enabled: true, index: 0 } } } }
    const end = { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'result', type: 'Any', value: '{{list.item}}' }] } } }
    const configured = [start, variable, extract, list, end]
    const edges = [{ source: 'start', target: 'variable' }, { source: 'variable', target: 'extract' }, { source: 'extract', target: 'list' }, { source: 'list', target: 'end' }]
    expect(validateWorkflowGraph(configured, edges).map(issue => issue.code)).toEqual(expect.arrayContaining([
      'variableAssignmentsInvalid', 'extractFieldsRequired', 'extractModelRequired', 'listSettingsInvalid',
    ]))
  })

  it('validates inline Python code inputs, outputs, and runtime limits', () => {
    const start = { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['form'], input_fields: [{ name: 'message' }] } } }
    const code = { id: 'code', type: 'code', position: { x: 0, y: 0 }, data: { nodeType: 'code', label: 'Code', config: { source: 'print("missing main")', entrypoint: 'bad-name', inputs: [{ name: 'arg', value: '' }, { name: 'arg', value: 'x' }], outputs: [], timeout_seconds: 0, memory_mb: 20 } } }
    const end = { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'result', type: 'Any', value: '{{code.result}}' }] } } }
    const issues = validateWorkflowGraph([start, code, end], [{ source: 'start', target: 'code' }, { source: 'code', target: 'end' }]).map(issue => issue.code)
    expect(issues).toEqual(expect.arrayContaining(['codeSourceInvalid', 'codeEntrypointInvalid', 'codeInputsInvalid', 'codeOutputsInvalid', 'codeRuntimeInvalid']))
  })

  it('validates iteration containers and isolates child connections', () => {
    const start = { ...nodes[0], data: { nodeType: 'start', config: { triggers: ['form'], input_fields: [] } } }
    const iteration = { id: 'iteration', type: 'iteration', position: { x: 0, y: 0 }, data: { nodeType: 'iteration', label: 'Iteration', config: { source: [1, 2], item_variable: 'item', mode: 'sequential', concurrency: 1 } } }
    const child = { id: 'child', type: 'template', parentNode: 'iteration', position: { x: 120, y: 80 }, data: { nodeType: 'template', label: 'Child', config: { inputs: [{ name: 'value', value: '{{item}}' }], template: '{{ value }}' } } }
    const end = { ...nodes[2], data: { nodeType: 'end', config: { outputs: [{ name: 'result', type: 'Any', value: '{{iteration.results}}' }] } } }
    const graphNodes = [start, iteration, child, end]
    const graphEdges = [{ source: 'start', target: 'iteration' }, { source: 'iteration', target: 'end' }]

    expect(validateWorkflowGraph(graphNodes, graphEdges)).toEqual([])
    expect(isConnectionAllowed(graphNodes, graphEdges, { source: 'start', target: 'child' })).toBe(false)
    expect(isConnectionAllowed(graphNodes, graphEdges, { source: 'child', target: 'end' })).toBe(false)
    expect(validateWorkflowGraph([start, iteration, end], graphEdges).map(issue => issue.code)).toContain('containerBodyRequired')
  })

  it('validates wait nodes', () => {
    const start = { ...nodes[0], data: { nodeType: 'start', label: 'Start', config: { triggers: ['api'], input_fields: [] } } }
    const branch = (id: string) => ({ id, type: 'template', position: { x: 0, y: 0 }, data: { nodeType: 'template', label: id, config: { inputs: [], template: id } } })
    const wait = { id: 'wait', type: 'wait', position: { x: 0, y: 0 }, data: { nodeType: 'wait', label: 'Wait', config: { mode: 'all' } } }
    const end = { ...nodes[2], data: { nodeType: 'end', label: 'End', config: { outputs: [{ name: 'completed', type: 'Boolean', value: '{{wait.completed}}' }] } } }
    const graphNodes = [start, branch('a'), branch('b'), wait, end]
    const graphEdges = [
      { source: 'start', target: 'a' }, { source: 'start', target: 'b' },
      { source: 'a', target: 'wait' }, { source: 'b', target: 'wait' },
      { source: 'wait', target: 'end' },
    ]

    expect(validateWorkflowGraph(graphNodes, graphEdges)).toEqual([])
    expect(validateWorkflowGraph(graphNodes, graphEdges.filter(edge => !(edge.source === 'b' && edge.target === 'wait'))).map(issue => issue.code)).toContain('waitIncomingRequired')
  })

  it('keeps annotations outside connections, layout, and validation', () => {
    const note = { id: 'note', type: 'note', position: { x: 777, y: 333 }, data: { nodeType: 'note', label: 'Reminder' } }
    expect(isConnectionAllowed([...nodes, note], [], { source: 'start', target: 'note' })).toBe(false)
    expect(isConnectionAllowed([...nodes, note], [], { source: 'note', target: 'end' })).toBe(false)
    const laidOut = layoutWorkflow([...nodes, note], [])
    expect(laidOut.find(node => node.id === 'note')!.position).toEqual({ x: 777, y: 333 })
    const issues = validateWorkflowGraph([...nodes, note], [
      { id: 'a', source: 'start', target: 'task' },
      { id: 'b', source: 'task', target: 'end' },
    ])
    expect(issues.map(issue => issue.code)).toContain('llmModelRequired')
    expect(issues.some(issue => issue.nodeId === 'note')).toBe(false)
  })

  it('inserts a node into an edge without losing branch handles', () => {
    const branchEdge = { id: 'branch', source: 'condition', target: 'end', sourceHandle: 'true', targetHandle: 'input', type: 'workflow', selected: true }
    const inserted = { id: 'writer', type: 'llm', position: { x: 300, y: 120 }, data: { nodeType: 'llm' } }
    const result = insertNodeOnEdge(nodes, [branchEdge], 'branch', inserted)

    expect(result.nodes.at(-1)).toEqual(inserted)
    expect(result.edges).toHaveLength(2)
    expect(result.edges).toEqual(expect.arrayContaining([
      expect.objectContaining({ source: 'condition', target: 'writer', sourceHandle: 'true' }),
      expect.objectContaining({ source: 'writer', target: 'end', targetHandle: 'input' }),
    ]))
    expect(result.edges.find(edge => edge.target === 'writer')).not.toHaveProperty('targetHandle')
    expect(result.edges.find(edge => edge.source === 'writer')).not.toHaveProperty('sourceHandle')
    expect(result.edges.every(edge => !('selected' in edge))).toBe(true)
  })

  it('replaces a node in place and keeps compatible connections', () => {
    const replacement = { id: 'task', type: 'condition', position: { x: 200, y: 100 }, data: { nodeType: 'condition', label: 'Router', config: { conditions: [] } } }
    const result = replaceWorkflowNode(nodes as any[], [
      { id: 'in', source: 'start', target: 'task', targetHandle: 'input' },
      { id: 'out-a', source: 'task', target: 'end' },
      { id: 'out-b', source: 'task', target: 'other' },
    ] as any[], 'task', replacement as any)

    expect(result.nodes.find(node => node.id === 'task')).toBe(replacement)
    expect(result.edges.find(edge => edge.id === 'in')).not.toHaveProperty('targetHandle')
    expect(result.edges.find(edge => edge.id === 'out-a')?.sourceHandle).toBe('true')
    expect(result.edges.find(edge => edge.id === 'out-b')?.sourceHandle).toBe('false')
  })

  it('drops incompatible incoming or outgoing connections when replacing boundary nodes', () => {
    const connected = [{ id: 'in', source: 'start', target: 'task' }, { id: 'out', source: 'task', target: 'end' }]
    const newStart = { id: 'task', type: 'start', position: { x: 0, y: 0 }, data: { nodeType: 'start', config: {} } }
    const startResult = replaceWorkflowNode(nodes as any[], connected as any[], 'task', newStart as any)
    expect(startResult.edges.map(edge => edge.id)).toEqual(['out'])

    const newEnd = { id: 'task', type: 'end', position: { x: 0, y: 0 }, data: { nodeType: 'end', config: {} } }
    const endResult = replaceWorkflowNode(nodes as any[], connected as any[], 'task', newEnd as any)
    expect(endResult.edges.map(edge => edge.id)).toEqual(['in'])
  })
})
