type GraphElement = { id: string; data: Record<string, any>; [key: string]: any }
type GraphEdge = GraphElement & { source: string; target: string }

export const RUNTIME_DATA_KEYS = new Set(['runtimeStatus', 'runtimeDurationMs', 'runtimeRunId', 'validationMessages'])

function validationData(data: Record<string, any> | undefined): Record<string, any> {
  return Array.isArray(data?.validationMessages) && data.validationMessages.length ? { validationMessages: data.validationMessages } : {}
}

export function stripRuntimeData(data: Record<string, any> | undefined) {
  return Object.fromEntries(Object.entries(data || {}).filter(([key]) => !RUNTIME_DATA_KEYS.has(key)))
}

function durationMs(trace: any) {
  if (!trace?.started_at || !trace?.finished_at) return null
  const duration = new Date(trace.finished_at).getTime() - new Date(trace.started_at).getTime()
  return Number.isFinite(duration) && duration >= 0 ? duration : null
}

export function buildRunOverlay(nodes: GraphElement[], edges: GraphEdge[], run: any) {
  const traces = Array.isArray(run?.trace) ? run.trace : []
  const traceByNode = new Map(traces.map((trace: any) => [String(trace.node_id), trace]))
  const fullRun = run?.triggered_by !== 'node'
  const runId = run?.id || run?.run_id || ''

  const nextNodes: GraphElement[] = nodes.map(node => {
    const trace: any = traceByNode.get(node.id)
    const validation = validationData(node.data)
    const data = stripRuntimeData(node.data)
    if (trace) return { ...node, data: { ...data, ...validation, runtimeStatus: trace.status || 'succeeded', runtimeDurationMs: durationMs(trace), runtimeRunId: runId } }
    if (fullRun && String(data.nodeType || node.type) !== 'note') return { ...node, data: { ...data, ...validation, runtimeStatus: 'skipped', runtimeRunId: runId } }
    return { ...node, data: { ...data, ...validation } }
  })

  const nextEdges: GraphEdge[] = edges.map(edge => {
    const data = stripRuntimeData(edge.data)
    if (!fullRun) return { ...edge, data }
    const sourceTrace: any = traceByNode.get(edge.source)
    const branch = sourceTrace?.output?.branch
    const branchMatches = !branch || String(edge.sourceHandle || '') === String(branch)
    const active = Boolean(sourceTrace) && traceByNode.has(edge.target) && branchMatches
    return { ...edge, data: { ...data, runtimeStatus: active ? 'active' : 'skipped', runtimeRunId: runId } }
  })

  return {
    nodes: nextNodes,
    edges: nextEdges,
    nodeResults: Object.fromEntries(traces.map((trace: any) => [trace.node_id, trace])),
    runId,
  }
}

export function clearRunOverlay(nodes: GraphElement[], edges: GraphEdge[]) {
  return {
    nodes: nodes.map(node => ({ ...node, data: { ...stripRuntimeData(node.data), ...validationData(node.data) } })),
    edges: edges.map(edge => ({ ...edge, data: stripRuntimeData(edge.data) })),
  }
}
