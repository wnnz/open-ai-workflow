export type WorkflowPoint = { x: number; y: number }
export type WorkflowNodeLike = { id: string; type?: string; position: WorkflowPoint; parentNode?: string; extent?: string; data?: Record<string, any>; dimensions?: { width?: number; height?: number }; style?: Record<string, any> }
export type WorkflowEdgeLike = {
  id?: string
  source: string
  target: string
  sourceHandle?: string | null
  targetHandle?: string | null
  type?: string
  data?: Record<string, any>
  animated?: boolean
  style?: Record<string, any>
  markerStart?: string
  markerEnd?: string
}
export type WorkflowConnectionLike = {
  id?: string
  source?: string | null
  target?: string | null
  sourceHandle?: string | null
  targetHandle?: string | null
}
export type WorkflowValidationIssue = {
  code: string
  nodeId?: string
  params?: Record<string, string | number>
}
const executionPolicyNodeTypes = new Set(['llm', 'image', 'agent', 'code', 'script', 'template', 'variable', 'json', 'aggregate', 'extract', 'list', 'http', 'iteration', 'loop', 'delay', 'subworkflow', 'document', 'answer_filler'])

type MergeableWorkflowEdge = {
  id?: string
  source: string
  target: string
  sourceHandle?: unknown
  targetHandle?: unknown
}

export function mergeWorkflowEdges<T extends MergeableWorkflowEdge>(...collections: T[][]): T[] {
  const merged = new Map<string, T>()
  for (const edges of collections) {
    for (const edge of edges) {
      const key = String(edge.id || `${edge.source}|${String(edge.sourceHandle || '')}|${edge.target}|${String(edge.targetHandle || '')}`)
      merged.set(key, edge)
    }
  }
  return [...merged.values()]
}

export function clearWorkflowEdgeSelection<T extends object>(edges: T[]): T[] {
  return edges.map(edge => (edge as { selected?: boolean }).selected ? { ...edge, selected: false } : edge)
}

export function removeWorkflowEdgeById<T extends { id?: string }>(edges: T[], edgeId: string): T[] {
  return edges.filter(edge => edge.id !== edgeId)
}

function nodeType(node: WorkflowNodeLike | undefined) {
  return String(node?.data?.nodeType || node?.type || '')
}

function numericNodeSize(node: WorkflowNodeLike, key: 'width' | 'height', fallback: number) {
  const styled = Number.parseFloat(String(node.style?.[key] || ''))
  if (Number.isFinite(styled) && styled > 0) return styled
  const measured = Number(node.dimensions?.[key])
  return Number.isFinite(measured) && measured > 0 ? measured : fallback
}

export function absoluteNodePosition(nodes: WorkflowNodeLike[], nodeId: string): WorkflowPoint {
  const byId = new Map(nodes.map(node => [node.id, node]))
  const node = byId.get(nodeId)
  if (!node) return { x: 0, y: 0 }
  const position = { ...node.position }
  const visited = new Set([node.id])
  let parentId = node.parentNode
  while (parentId && !visited.has(parentId)) {
    visited.add(parentId)
    const parent = byId.get(parentId)
    if (!parent) break
    position.x += parent.position.x
    position.y += parent.position.y
    parentId = parent.parentNode
  }
  return position
}

export function nextContainerChildPosition(nodes: WorkflowNodeLike[], parentId: string): WorkflowPoint {
  const children = nodes.filter(node => node.parentNode === parentId && nodeType(node) !== 'note')
  if (!children.length) return { x: 230, y: 84 }
  const bottom = Math.max(...children.map(node => node.position.y + numericNodeSize(node, 'height', 82)))
  return { x: 230, y: Math.ceil(bottom + 18) }
}

export function containerSizeForChildren(
  nodes: WorkflowNodeLike[], parentId: string,
  options: { minWidth?: number; minHeight?: number; rightPadding?: number; bottomPadding?: number } = {},
) {
  const children = nodes.filter(node => node.parentNode === parentId && nodeType(node) !== 'note')
  const minWidth = options.minWidth ?? 520
  const minHeight = options.minHeight ?? 260
  const rightPadding = options.rightPadding ?? 36
  const bottomPadding = options.bottomPadding ?? 36
  if (!children.length) return { width: minWidth, height: minHeight }
  const right = Math.max(...children.map(node => node.position.x + numericNodeSize(node, 'width', 206)))
  const bottom = Math.max(...children.map(node => node.position.y + numericNodeSize(node, 'height', 82)))
  return {
    width: Math.max(minWidth, Math.ceil(right + rightPadding)),
    height: Math.max(minHeight, Math.ceil(bottom + bottomPadding)),
  }
}

export function containerEntryPoints(nodes: WorkflowNodeLike[], edges: WorkflowEdgeLike[], parentId: string) {
  const children = nodes.filter(node => node.parentNode === parentId && nodeType(node) !== 'note')
  const childIds = new Set(children.map(node => node.id))
  const connectedTargets = new Set(edges
    .filter(edge => childIds.has(edge.source) && childIds.has(edge.target))
    .map(edge => edge.target))
  return children
    .filter(node => !connectedTargets.has(node.id))
    .map(node => ({
      nodeId: node.id,
      x: node.position.x,
      y: node.position.y + numericNodeSize(node, 'height', 82) / 2,
    }))
}

export function findAvailableNodePosition(
  nodes: WorkflowNodeLike[],
  desired: WorkflowPoint,
  options: { parentNode?: string | null; ignoreIds?: string[]; horizontalGap?: number; verticalGap?: number } = {},
) {
  const parentNode = options.parentNode || null
  const ignored = new Set(options.ignoreIds || [])
  const horizontalGap = options.horizontalGap ?? 230
  const verticalGap = options.verticalGap ?? 120
  const peers = nodes.filter(node => !ignored.has(node.id) && (node.parentNode || null) === parentNode && nodeType(node) !== 'note')
  const collides = (candidate: WorkflowPoint) => peers.some(node => (
    Math.abs(node.position.x - candidate.x) < horizontalGap
    && Math.abs(node.position.y - candidate.y) < verticalGap
  ))

  if (!collides(desired)) return desired
  for (let step = 1; step <= 20; step += 1) {
    const below = { x: desired.x, y: desired.y + step * verticalGap }
    if (!collides(below)) return below
    const above = { x: desired.x, y: desired.y - step * verticalGap }
    if (!collides(above)) return above
  }
  return { x: desired.x + horizontalGap, y: desired.y }
}

export function isConnectionAllowed(
  nodes: WorkflowNodeLike[],
  edges: WorkflowEdgeLike[],
  connection: WorkflowConnectionLike,
) {
  const source = connection.source
  const target = connection.target
  if (!source || !target || source === target) return false
  if ([source, target].some(id => nodeType(nodes.find(node => node.id === id)) === 'note')) return false
  if (nodeType(nodes.find(node => node.id === source)) === 'end') return false
  if (nodeType(nodes.find(node => node.id === target)) === 'start') return false
  const existingConnection = Boolean(connection.id && edges.some(edge => edge.id === connection.id))
  if (!existingConnection && edges.some(edge => (
    edge.source === source
    && edge.target === target
    && String(edge.sourceHandle || '') === String(connection.sourceHandle || '')
    && String(edge.targetHandle || '') === String(connection.targetHandle || '')
  ))) return false
  const sourceNode = nodes.find(node => node.id === source)
  const targetNode = nodes.find(node => node.id === target)
  if ((sourceNode?.parentNode || null) !== (targetNode?.parentNode || null)) return false

  const outgoing = new Map<string, string[]>()
  for (const edge of edges) outgoing.set(edge.source, [...(outgoing.get(edge.source) || []), edge.target])
  const pending = [target]
  const visited = new Set<string>()
  while (pending.length) {
    const current = pending.pop()!
    if (current === source) return false
    if (visited.has(current)) continue
    visited.add(current)
    pending.push(...(outgoing.get(current) || []))
  }
  return true
}

export function insertNodeOnEdge<TNode extends WorkflowNodeLike, TEdge extends WorkflowEdgeLike>(
  nodes: TNode[],
  edges: TEdge[],
  edgeId: string,
  node: TNode,
) {
  const edge = edges.find(item => item.id === edgeId)
  if (!edge) return { nodes, edges }

  // Vue Flow enriches rendered edges with internal node references. Reusing the
  // whole object leaves stale references behind, so rebuild only persisted fields.
  const shared = {
    type: 'workflow',
    data: edge.data,
    animated: edge.animated,
    style: edge.style,
    markerStart: edge.markerStart,
    markerEnd: edge.markerEnd,
  }
  const before = {
    ...shared,
    id: `${edgeId}-before-${node.id}`,
    source: edge.source,
    target: node.id,
    sourceHandle: edge.sourceHandle || undefined,
  } as TEdge
  const after = {
    ...shared,
    id: `${edgeId}-after-${node.id}`,
    source: node.id,
    target: edge.target,
    targetHandle: edge.targetHandle || undefined,
  } as TEdge
  return {
    nodes: [...nodes, node],
    edges: [...edges.filter(item => item.id !== edgeId), before, after],
  }
}

export function replaceWorkflowNode<TNode extends WorkflowNodeLike, TEdge extends WorkflowEdgeLike>(
  nodes: TNode[],
  edges: TEdge[],
  nodeId: string,
  replacement: TNode,
) {
  if (!nodes.some(node => node.id === nodeId)) return { nodes, edges }
  const replacementType = nodeType(replacement)
  const outgoing = edges.filter(edge => edge.source === nodeId)
  const classifierHandles = replacementType === 'classifier'
    ? (replacement.data?.config?.categories || []).map((category: any) => `category:${category.id}`)
    : replacementType === 'human'
      ? (replacement.data?.config?.actions || []).map((action: any) => `action:${action.id}`)
      : []
  let outgoingIndex = 0

  const nextEdges = edges.flatMap(edge => {
    if (edge.target === nodeId && ['start', 'note'].includes(replacementType)) return []
    if (edge.source !== nodeId) {
      const retained = { ...edge }
      if (edge.target === nodeId) delete retained.targetHandle
      return [retained as TEdge]
    }
    if (['end', 'note'].includes(replacementType)) return []

    const index = outgoingIndex++
    let sourceHandle: string | undefined
    if (replacementType === 'condition') sourceHandle = index === 0 ? 'true' : 'false'
    else if (classifierHandles.length) sourceHandle = classifierHandles[index % classifierHandles.length]
    const data = { ...(edge.data || {}) }
    delete data.branchLabel
    return [{ ...edge, sourceHandle, data } as TEdge]
  })

  return {
    nodes: nodes.map(node => node.id === nodeId ? replacement : node),
    edges: nextEdges,
    removedEdgeCount: edges.length - nextEdges.length,
    retainedOutgoingCount: Math.min(outgoing.length, nextEdges.filter(edge => edge.source === nodeId).length),
  }
}

export function layoutWorkflow<T extends WorkflowNodeLike>(nodes: T[], edges: WorkflowEdgeLike[]): T[] {
  if (nodes.some(node => nodeType(node) === 'note')) {
    const flowNodes = nodes.filter(node => nodeType(node) !== 'note')
    const positioned = new Map(layoutWorkflow(flowNodes, edges).map(node => [node.id, node.position]))
    return nodes.map(node => positioned.has(node.id) ? { ...node, position: positioned.get(node.id)! } : node)
  }
  const nodeIds = new Set(nodes.map(node => node.id))
  const validEdges = edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  if (!validEdges.length) {
    const rank = (node: T) => nodeType(node) === 'start' ? 0 : nodeType(node) === 'end' ? 2 : 1
    const ordered = [...nodes].sort((left, right) => rank(left) - rank(right))
    let cursorX = 100
    const positions = new Map(ordered.map(node => {
      const position = { x: cursorX, y: 180 }
      cursorX += numericNodeSize(node, 'width', 206) + 80
      return [node.id, position] as const
    }))
    return nodes.map(node => ({ ...node, position: positions.get(node.id)! }))
  }
  const incoming = new Map(nodes.map(node => [node.id, 0]))
  const outgoing = new Map(nodes.map(node => [node.id, [] as string[]]))
  for (const edge of validEdges) {
    incoming.set(edge.target, (incoming.get(edge.target) || 0) + 1)
    outgoing.get(edge.source)!.push(edge.target)
  }

  const layer = new Map<string, number>()
  const queue = nodes
    .filter(node => incoming.get(node.id) === 0)
    .sort((left, right) => Number(nodeType(right) === 'start') - Number(nodeType(left) === 'start'))
  for (const node of queue) layer.set(node.id, 0)
  for (let index = 0; index < queue.length; index += 1) {
    const current = queue[index]
    for (const target of outgoing.get(current.id) || []) {
      layer.set(target, Math.max(layer.get(target) || 0, (layer.get(current.id) || 0) + 1))
      incoming.set(target, (incoming.get(target) || 0) - 1)
      if (incoming.get(target) === 0) queue.push(nodes.find(node => node.id === target)!)
    }
  }

  let overflowLayer = Math.max(0, ...layer.values()) + 1
  for (const node of nodes) if (!layer.has(node.id)) layer.set(node.id, overflowLayer++)
  const groups = new Map<number, T[]>()
  for (const node of nodes) {
    const nodeLayer = layer.get(node.id) || 0
    groups.set(nodeLayer, [...(groups.get(nodeLayer) || []), node])
  }

  const orderedLayers = [...groups.keys()].sort((left, right) => left - right)
  for (const group of groups.values()) group.sort((left, right) => left.position.y - right.position.y || left.position.x - right.position.x)
  const predecessors = new Map(nodes.map(node => [node.id, [] as string[]]))
  for (const edge of validEdges) predecessors.get(edge.target)!.push(edge.source)
  const currentOrder = () => {
    const order = new Map<string, number>()
    for (const group of groups.values()) group.forEach((node, index) => order.set(node.id, index))
    return order
  }
  const reorderLayer = (nodeLayer: number, neighbors: Map<string, string[]>) => {
    const group = groups.get(nodeLayer)
    if (!group || group.length < 2) return
    const order = currentOrder()
    const score = (node: T) => {
      const values = (neighbors.get(node.id) || []).map(id => order.get(id)).filter((value): value is number => value !== undefined)
      return values.length ? values.reduce((total, value) => total + value, 0) / values.length : null
    }
    group.sort((left, right) => {
      const leftScore = score(left)
      const rightScore = score(right)
      if (leftScore === null && rightScore === null) return 0
      if (leftScore === null) return 1
      if (rightScore === null) return -1
      return leftScore - rightScore
    })
  }
  for (let pass = 0; pass < 4; pass += 1) {
    for (const nodeLayer of orderedLayers.slice(1)) reorderLayer(nodeLayer, predecessors)
    for (const nodeLayer of [...orderedLayers].reverse().slice(1)) reorderLayer(nodeLayer, outgoing)
  }
  const layerX = new Map<number, number>()
  let cursorX = 100
  for (const nodeLayer of orderedLayers) {
    layerX.set(nodeLayer, cursorX)
    cursorX += Math.max(...groups.get(nodeLayer)!.map(node => numericNodeSize(node, 'width', 206))) + 80
  }

  const positions = new Map<string, WorkflowPoint>()
  for (const [nodeLayer, group] of groups) {
    const heights = group.map(node => numericNodeSize(node, 'height', 82))
    const totalHeight = heights.reduce((total, height) => total + height, 0) + Math.max(0, group.length - 1) * 48
    let cursorY = Math.max(80, 180 - totalHeight / 2)
    group.forEach((node, index) => {
      positions.set(node.id, { x: layerX.get(nodeLayer)!, y: cursorY })
      cursorY += heights[index] + 48
    })
  }
  return nodes.map(node => ({ ...node, position: positions.get(node.id)! }))
}

export function layoutContainerChildren<T extends WorkflowNodeLike>(nodes: T[], edges: WorkflowEdgeLike[]): T[] {
  const nodeIds = new Set(nodes.map(node => node.id))
  const internalEdges = edges.filter(edge => nodeIds.has(edge.source) && nodeIds.has(edge.target))
  if (!internalEdges.length) {
    let cursorY = 84
    return [...nodes]
      .sort((left, right) => left.position.y - right.position.y || left.position.x - right.position.x)
      .map(node => {
        const positioned = { ...node, position: { x: 230, y: cursorY } }
        cursorY += numericNodeSize(node, 'height', 82) + 18
        return positioned
      })
  }
  const arranged = layoutWorkflow(nodes, internalEdges)
  const minX = Math.min(...arranged.map(node => node.position.x))
  const minY = Math.min(...arranged.map(node => node.position.y))
  return arranged.map(node => ({ ...node, position: { x: node.position.x - minX + 230, y: node.position.y - minY + 84 } }))
}

export function validateWorkflowGraph(
  nodes: WorkflowNodeLike[],
  edges: WorkflowEdgeLike[],
): WorkflowValidationIssue[] {
  const issues: WorkflowValidationIssue[] = []
  const nodeById = new Map(nodes.map(node => [node.id, node]))
  const starts = nodes.filter(node => !node.parentNode && nodeType(node) === 'start')
  const ends = nodes.filter(node => !node.parentNode && nodeType(node) === 'end')

  if (starts.length !== 1) issues.push({ code: starts.length ? 'multipleStarts' : 'missingStart' })
  if (ends.length < 1) issues.push({ code: 'missingEnd' })

  const validEdges = edges.filter(edge => {
    const sourceNode = nodeById.get(edge.source)
    const targetNode = nodeById.get(edge.target)
    if (sourceNode && targetNode && (sourceNode.parentNode || null) === (targetNode.parentNode || null)) return true
    issues.push({ code: 'invalidEdge' })
    return false
  })
  const incoming = new Map(nodes.map(node => [node.id, [] as WorkflowEdgeLike[]]))
  const outgoing = new Map(nodes.map(node => [node.id, [] as WorkflowEdgeLike[]]))
  for (const edge of validEdges) {
    incoming.get(edge.target)!.push(edge)
    outgoing.get(edge.source)!.push(edge)
  }

  for (const node of nodes) {
    const type = nodeType(node)
    const config = node.data?.config || {}
    const label = String(node.data?.label || node.id)
    const params = { label }

    if (type === 'note') continue

    if (type === 'start') {
      const triggers = Array.isArray(config.triggers) ? config.triggers : []
      if (!triggers.length) issues.push({ code: 'startTriggerRequired', nodeId: node.id, params })
      else if (triggers.length > 1) issues.push({ code: 'startTriggerExclusive', nodeId: node.id, params })
      const fields = Array.isArray(config.input_fields) ? config.input_fields : []
      const names: string[] = fields.map((field: any) => String(field?.name || ''))
      if (names.some(name => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(name))) {
        issues.push({ code: 'invalidInputName', nodeId: node.id, params })
      } else if (new Set(names).size !== names.length) {
        issues.push({ code: 'duplicateInputName', nodeId: node.id, params })
      }
      if (fields.some((field: any) => field?.type === 'select' && (!Array.isArray(field.options) || !field.options.length || field.options.some((option: any) => !String(option || '').trim()) || new Set(field.options).size !== field.options.length))) {
        issues.push({ code: 'inputSelectOptionsRequired', nodeId: node.id, params })
      }
      if (!(outgoing.get(node.id)?.length)) issues.push({ code: 'startNotConnected', nodeId: node.id, params })
      continue
    }

    if (type === 'end') {
      if (!(incoming.get(node.id)?.length)) issues.push({ code: 'endNotConnected', nodeId: node.id, params })
      const outputs = Array.isArray(config.outputs) ? config.outputs : []
      const outputNames: string[] = outputs.map((output: any) => String(output?.name || ''))
      if (!outputs.length) issues.push({ code: 'endOutputRequired', nodeId: node.id, params })
      else if (outputNames.some(name => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(name))) issues.push({ code: 'invalidOutputName', nodeId: node.id, params })
      else if (new Set(outputNames).size !== outputNames.length) issues.push({ code: 'duplicateOutputName', nodeId: node.id, params })
      if (outputs.some((output: any) => output?.value == null || output.value === '')) issues.push({ code: 'endOutputValueRequired', nodeId: node.id, params })
      continue
    }

    const nodeOutgoing = outgoing.get(node.id) || []
    const normalOutgoing = nodeOutgoing.filter(edge => String(edge.sourceHandle || '') !== 'error')
    if (!node.parentNode && (!(incoming.get(node.id)?.length) || !normalOutgoing.length)) {
      issues.push({ code: 'nodeNotConnected', nodeId: node.id, params })
    }
    if (executionPolicyNodeTypes.has(type)) {
      const retry = config.retry || { enabled: false }
      if (retry.enabled && (!Number.isInteger(Number(retry.max_retries)) || Number(retry.max_retries) < 1 || Number(retry.max_retries) > 10 || Number(retry.interval_seconds) < 0 || Number(retry.interval_seconds) > 30)) issues.push({ code: 'retryPolicyInvalid', nodeId: node.id, params })
      const strategy = config.error_strategy || 'fail'
      if (!['fail', 'default_value', 'error_branch'].includes(strategy) || (strategy === 'default_value' && (!config.default_output || typeof config.default_output !== 'object' || Array.isArray(config.default_output)))) issues.push({ code: 'errorStrategyInvalid', nodeId: node.id, params })
      const errorEdges = nodeOutgoing.filter(edge => String(edge.sourceHandle || '') === 'error')
      if (strategy === 'error_branch' && !errorEdges.length) issues.push({ code: 'errorBranchRequired', nodeId: node.id, params })
      if (strategy !== 'error_branch' && errorEdges.length) issues.push({ code: 'unexpectedErrorBranch', nodeId: node.id, params })
    }
    if (type === 'llm') {
      if (!String(config.model || '').trim()) issues.push({ code: 'llmModelRequired', nodeId: node.id, params })
      const messages = Array.isArray(config.messages) ? config.messages : []
      if ((!messages.length || messages.some((message: any) => !['system', 'user', 'assistant'].includes(message?.role) || !String(message?.content || '').trim())) && !String(config.prompt || '').trim()) issues.push({ code: 'llmMessagesRequired', nodeId: node.id, params })
      if (Number(config.temperature) < 0 || Number(config.temperature) > 2 || Number(config.top_p) < 0 || Number(config.top_p) > 1 || Number(config.max_tokens) < 1 || Number(config.max_tokens) > 128000) issues.push({ code: 'llmParametersInvalid', nodeId: node.id, params })
      if (config.response_format === 'json_schema' && (!config.response_schema || typeof config.response_schema !== 'object' || Array.isArray(config.response_schema))) issues.push({ code: 'llmSchemaRequired', nodeId: node.id, params })
    }
    if (type === 'image') {
      if (!String(config.provider_id || '').trim() || !String(config.model || '').trim()) issues.push({ code: 'imageModelRequired', nodeId: node.id, params })
      if (!String(config.prompt || '').trim()) issues.push({ code: 'imageInputsRequired', nodeId: node.id, params })
      const variableCount = typeof config.count === 'string' && /\{\{[^{}]+\}\}/.test(config.count)
      if ((!variableCount && (!Number.isInteger(Number(config.count)) || Number(config.count) < 1 || Number(config.count) > 10)) || !['auto','low','medium','high'].includes(config.quality || 'high') || !['webp','png','jpeg','jpg'].includes(config.output_format || 'webp') || Number(config.output_compression) < 0 || Number(config.output_compression) > 100 || Number(config.timeout_seconds ?? 600) < 30 || Number(config.timeout_seconds ?? 600) > 900) issues.push({ code: 'imageParametersInvalid', nodeId: node.id, params })
    }
    if (type === 'agent' && !String(config.model || '').trim()) issues.push({ code: 'agentModelRequired', nodeId: node.id, params })
    if (type === 'classifier') {
      if (!String(config.input || '').trim()) issues.push({ code: 'classifierInputRequired', nodeId: node.id, params })
      const categories = Array.isArray(config.categories) ? config.categories : []
      const categoryIds: string[] = categories.map((category: any) => String(category?.id || ''))
      const categoryNames: string[] = categories.map((category: any) => String(category?.name || '').trim())
      if (categories.length < 2 || categoryIds.some(id => !/^[A-Za-z0-9_-]{1,64}$/.test(id)) || new Set(categoryIds).size !== categoryIds.length || categoryNames.some(name => !name) || new Set(categoryNames).size !== categoryNames.length) issues.push({ code: 'classifierCategoriesRequired', nodeId: node.id, params })
      const handles = new Set((outgoing.get(node.id) || []).map(edge => String((edge as any).sourceHandle || '')))
      if (categoryIds.some(id => !handles.has(`category:${id}`))) issues.push({ code: 'classifierBranchesRequired', nodeId: node.id, params })
    }
    if (type === 'script' && !String(config.script_id || '').trim()) issues.push({ code: 'scriptRequired', nodeId: node.id, params })
    if (type === 'code') {
      const inputs = Array.isArray(config.inputs) ? config.inputs : []
      const inputNames = inputs.map((item: any) => String(item?.name || ''))
      const outputs = Array.isArray(config.outputs) ? config.outputs : []
      const outputNames = outputs.map((item: any) => String(item?.name || ''))
      if (!String(config.source || '').trim() || !/^\s*(async\s+)?def\s+[A-Za-z_][A-Za-z0-9_]*\s*\(/m.test(String(config.source || ''))) issues.push({ code: 'codeSourceInvalid', nodeId: node.id, params })
      if (!/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(config.entrypoint || 'main'))) issues.push({ code: 'codeEntrypointInvalid', nodeId: node.id, params })
      if (inputs.some((item: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(item?.name || '')) || item?.value === undefined) || new Set(inputNames).size !== inputNames.length) issues.push({ code: 'codeInputsInvalid', nodeId: node.id, params })
      if (!outputs.length || outputs.some((item: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(item?.name || '')) || !['String','Number','Boolean','Object','Array','File','Any'].includes(item?.type || 'Any')) || new Set(outputNames).size !== outputNames.length) issues.push({ code: 'codeOutputsInvalid', nodeId: node.id, params })
      if (!(Number(config.timeout_seconds ?? 30) >= 1 && Number(config.timeout_seconds ?? 30) <= 300) || !(Number(config.memory_mb ?? 256) >= 64 && Number(config.memory_mb ?? 256) <= 2048)) issues.push({ code: 'codeRuntimeInvalid', nodeId: node.id, params })
    }
    if (type === 'http') {
      const url = String(config.url || '').trim()
      if (!url) issues.push({ code: 'httpUrlRequired', nodeId: node.id, params })
      else if (!/^https?:\/\/\S+$/i.test(url) && !/^\{\{[^{}]+\}\}$/.test(url)) issues.push({ code: 'httpUrlInvalid', nodeId: node.id, params })
      if (!(Number(config.timeout_seconds ?? 30) >= 1 && Number(config.timeout_seconds ?? 30) <= 300)) issues.push({ code: 'httpTimeoutInvalid', nodeId: node.id, params })
      const responseLimit = Number(config.max_response_bytes ?? 2_000_000)
      if (!Number.isInteger(responseLimit) || responseLimit < 1024 || responseLimit > 10_000_000) issues.push({ code: 'httpResponseLimitInvalid', nodeId: node.id, params })
      const auth = config.auth || { type: 'none' }
      if ((auth.type === 'bearer' && !String(auth.token || '').trim())
        || (auth.type === 'basic' && !String(auth.username || '').trim())
        || (auth.type === 'api_key' && (!String(auth.key || '').trim() || !String(auth.value || '').trim()))) issues.push({ code: 'httpAuthIncomplete', nodeId: node.id, params })
    }
    if (type === 'condition') {
      const clauses = Array.isArray(config.conditions) ? config.conditions : []
      const hasStructuredRules = clauses.length > 0
      if (!hasStructuredRules && !String(config.expression || '').trim()) issues.push({ code: 'conditionRequired', nodeId: node.id, params })
      else if (hasStructuredRules && clauses.some((clause: any) => !String(clause?.variable || '').trim() || !String(clause?.operator || '').trim() || (!['is_empty', 'is_not_empty'].includes(clause.operator) && clause.value == null))) issues.push({ code: 'conditionClauseIncomplete', nodeId: node.id, params })
      const handles = new Set((outgoing.get(node.id) || []).map(edge => String((edge as any).sourceHandle || '')))
      if (!handles.has('true') || !handles.has('false')) issues.push({ code: 'conditionBranchesRequired', nodeId: node.id, params })
    }
    if (type === 'template') {
      if (!String(config.template || '').trim()) issues.push({ code: 'templateRequired', nodeId: node.id, params })
      const bindings = Array.isArray(config.inputs) ? config.inputs : []
      const names = bindings.map((binding: any) => String(binding?.name || ''))
      if (bindings.some((binding: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(binding?.name || '')) || !String(binding?.value || '').trim()) || new Set(names).size !== names.length) issues.push({ code: 'templateInputsInvalid', nodeId: node.id, params })
    }
    if (type === 'aggregate') {
      if (config.group_enabled) {
        const groups = Array.isArray(config.groups) ? config.groups : []
        const names = groups.map((group: any) => String(group?.name || ''))
        if (!groups.length || groups.some((group: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(group?.name || '')) || !(Array.isArray(group?.variables) && group.variables.some((value: any) => String(value || '').trim()))) || new Set(names).size !== names.length) issues.push({ code: 'aggregateGroupsInvalid', nodeId: node.id, params })
      } else if (!(Array.isArray(config.variables) && config.variables.some((value: any) => String(value || '').trim()))) issues.push({ code: 'aggregateVariablesRequired', nodeId: node.id, params })
    }
    if (type === 'extract') {
      if (!String(config.source || '').trim()) issues.push({ code: 'extractSourceRequired', nodeId: node.id, params })
      const fields = Array.isArray(config.fields) ? config.fields : []
      const names = fields.map((field: any) => String(field?.name || ''))
      if (!fields.length || fields.some((field: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(field?.name || ''))) || new Set(names).size !== names.length) issues.push({ code: 'extractFieldsRequired', nodeId: node.id, params })
      if (!String(config.model || '').trim()) issues.push({ code: 'extractModelRequired', nodeId: node.id, params })
    }
    if (type === 'variable') {
      const assignments = Array.isArray(config.assignments) ? config.assignments : []
      const names = assignments.map((assignment: any) => String(assignment?.name || ''))
      if (!assignments.length || assignments.some((assignment: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(assignment?.name || '')) || !['String','Number','Boolean','Object','Array','Any'].includes(assignment?.type || 'Any') || !['overwrite','append','extend','clear'].includes(assignment?.operation || 'overwrite') || (assignment?.operation !== 'clear' && assignment?.value === undefined)) || new Set(names).size !== names.length) issues.push({ code: 'variableAssignmentsInvalid', nodeId: node.id, params })
    }
    if (type === 'list') {
      if (!String(config.source || '').trim()) issues.push({ code: 'listSourceRequired', nodeId: node.id, params })
      if (config.filter?.enabled && (!String(config.filter.operator || '').trim() || (!['is_empty','is_not_empty'].includes(config.filter.operator) && config.filter.value === undefined))) issues.push({ code: 'listSettingsInvalid', nodeId: node.id, params })
      if (config.nth?.enabled && (!Number.isInteger(Number(config.nth.index)) || Number(config.nth.index) < 1)) issues.push({ code: 'listSettingsInvalid', nodeId: node.id, params })
      if (config.limit?.enabled && (!Number.isInteger(Number(config.limit.count)) || Number(config.limit.count) < 0)) issues.push({ code: 'listSettingsInvalid', nodeId: node.id, params })
      if (config.sort?.enabled && !['asc','desc'].includes(config.sort.order || 'asc')) issues.push({ code: 'listSettingsInvalid', nodeId: node.id, params })
    }
    if (type === 'human') {
      if (!String(config.form_content || config.instructions || '').trim()) issues.push({ code: 'approvalInstructionsRequired', nodeId: node.id, params })
      const methods = Array.isArray(config.submission_methods) ? config.submission_methods : []
      const actions = Array.isArray(config.actions) ? config.actions : []
      const actionIds = actions.map((action: any) => String(action?.id || ''))
      if (!methods.length || methods.some((method: string) => !['studio','link','email'].includes(method)) || !actions.length || actions.some((action: any) => !/^[A-Za-z_][A-Za-z0-9_]{0,63}$/.test(String(action?.id || '')) || !String(action?.label || '').trim()) || new Set(actionIds).size !== actionIds.length || !(Number(config.timeout_minutes) >= 1 && Number(config.timeout_minutes) <= 525600)) issues.push({ code: 'approvalSettingsInvalid', nodeId: node.id, params })
      const handles = new Set((outgoing.get(node.id) || []).map(edge => String((edge as any).sourceHandle || '')).filter(handle => handle.startsWith('action:')))
      if (actions.some((action: any) => !handles.has(`action:${action.id}`))) issues.push({ code: 'approvalBranchesRequired', nodeId: node.id, params })
    }
    if (type === 'wait') {
      if (!['all', 'any'].includes(config.mode || 'all')) issues.push({ code: 'waitModeInvalid', nodeId: node.id, params })
      if ((incoming.get(node.id) || []).length < 2) issues.push({ code: 'waitIncomingRequired', nodeId: node.id, params })
    }
    if (type === 'iteration') {
      if (!String(config.source || '').trim()) issues.push({ code: 'iterationSourceRequired', nodeId: node.id, params })
      if (!nodes.some(item => item.parentNode === node.id)) issues.push({ code: 'containerBodyRequired', nodeId: node.id, params })
      if (!['sequential', 'parallel'].includes(config.mode || 'sequential') || Number(config.concurrency || 1) < 1 || Number(config.concurrency || 1) > 20) issues.push({ code: 'iterationSettingsInvalid', nodeId: node.id, params })
    }
    if (type === 'loop') {
      if (!String(config.condition || '').trim()) issues.push({ code: 'loopConditionRequired', nodeId: node.id, params })
      if (!nodes.some(item => item.parentNode === node.id)) issues.push({ code: 'containerBodyRequired', nodeId: node.id, params })
      if (!Number.isInteger(Number(config.max_iterations)) || Number(config.max_iterations) < 1 || Number(config.max_iterations) > 100) issues.push({ code: 'loopSettingsInvalid', nodeId: node.id, params })
    }
    if (type === 'subworkflow' && !String(config.workflow_id || '').trim()) issues.push({ code: 'subworkflowRequired', nodeId: node.id, params })
    if (type === 'delay' && (!(Number(config.seconds) > 0) || Number(config.seconds) > 86400)) issues.push({ code: 'delayDurationInvalid', nodeId: node.id, params })
    if (type === 'document') {
      const operation = String(config.operation || 'extract')
      if (operation !== 'extract') issues.push({ code: 'documentOperationInvalid', nodeId: node.id, params })
      if (!String(config.source || '').trim()) issues.push({ code: 'documentSourceRequired', nodeId: node.id, params })
      if (!['text', 'text_tables', 'text_images'].includes(config.extract_mode || 'text')) issues.push({ code: 'documentSettingsInvalid', nodeId: node.id, params })
    }
    if (type === 'answer_filler') {
      if (!String(config.source || '').trim()) issues.push({ code: 'answerFillerSourceRequired', nodeId: node.id, params })
      if (!String(config.answers || '').trim()) issues.push({ code: 'answerFillerPlanRequired', nodeId: node.id, params })
    }
  }

  return issues
}
