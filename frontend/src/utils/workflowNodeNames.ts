import type { WorkflowNodeLike } from './workflowGraph'

export type NodeNameError = 'required' | 'invalid' | 'reserved' | 'duplicate'
export type NodeRename = { id: string; from: string; to: string }

const RESERVED_NAMES = new Set(['inputs', 'env', 'sys'])

function nodeType(node: WorkflowNodeLike) {
  return String(node.data?.nodeType || node.type || '')
}

function nameKey(value: string) {
  return value.trim().toLocaleLowerCase()
}

function escapeRegExp(value: string) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

export function nodeReferenceName(node: WorkflowNodeLike) {
  return String(node.data?.label || '').trim()
}

export function validateNodeName(nodes: WorkflowNodeLike[], nodeId: string, value: string): NodeNameError | null {
  const name = value.trim()
  if (!name) return 'required'
  if (/[.{}]/u.test(name)) return 'invalid'
  if (RESERVED_NAMES.has(nameKey(name))) return 'reserved'
  if (nodes.some(node => node.id !== nodeId && nameKey(nodeReferenceName(node)) === nameKey(name))) return 'duplicate'
  return null
}

export function nextUniqueNodeName(nodes: WorkflowNodeLike[], preferred: string, excludeIds: string[] = []) {
  const excluded = new Set(excludeIds)
  const used = new Set(nodes.filter(node => !excluded.has(node.id)).map(node => nameKey(nodeReferenceName(node))).filter(Boolean))
  const requested = preferred.trim() || 'Node'
  if (!RESERVED_NAMES.has(nameKey(requested)) && !used.has(nameKey(requested))) return requested

  const stem = requested.replace(/\d+$/u, '').trim() || requested
  const pattern = new RegExp(`^${escapeRegExp(stem)}(\\d+)?$`, 'iu')
  let nextIndex = 1
  for (const node of nodes) {
    if (excluded.has(node.id)) continue
    const match = nodeReferenceName(node).match(pattern)
    if (match?.[1]) nextIndex = Math.max(nextIndex, Number(match[1]) + 1)
  }
  while (used.has(nameKey(`${stem}${nextIndex}`)) || RESERVED_NAMES.has(nameKey(`${stem}${nextIndex}`))) nextIndex += 1
  return `${stem}${nextIndex}`
}

export function allocateDefaultNodeName(nodes: WorkflowNodeLike[], type: string, baseName: string) {
  const base = baseName.trim() || type || 'Node'
  const familyPattern = new RegExp(`^${escapeRegExp(base)}(\\d+)?$`, 'iu')
  const family = nodes.filter(node => nodeType(node) === type && familyPattern.test(nodeReferenceName(node)))
  if (!family.length && !validateNodeName(nodes, '__new__', base)) return { name: base, renames: [] as NodeRename[] }

  const renames: NodeRename[] = []
  const unnumbered = family.filter(node => nameKey(nodeReferenceName(node)) === nameKey(base))
  let nextIndex = family.reduce((maximum, node) => {
    const suffix = nodeReferenceName(node).match(familyPattern)?.[1]
    return Math.max(maximum, suffix ? Number(suffix) : 0)
  }, 0) + 1

  if (unnumbered.length) {
    for (const node of unnumbered) {
      const next = nextUniqueNodeName(nodes, `${base}${nextIndex}`, [node.id, ...renames.map(rename => rename.id)])
      renames.push({ id: node.id, from: nodeReferenceName(node), to: next })
      const suffix = next.match(/(\d+)$/u)?.[1]
      nextIndex = Math.max(nextIndex + 1, suffix ? Number(suffix) + 1 : nextIndex + 1)
    }
  }

  const virtualNodes = nodes.map(node => {
    const rename = renames.find(item => item.id === node.id)
    return rename ? { ...node, data: { ...node.data, label: rename.to } } : node
  })
  return { name: nextUniqueNodeName(virtualNodes, `${base}${nextIndex}`), renames }
}

export function ensureUniqueNodeNames<T extends WorkflowNodeLike>(nodes: T[], fallbackName: (node: T) => string) {
  const normalized = nodes.map(node => ({
    ...node,
    data: { ...node.data, label: nodeReferenceName(node) || fallbackName(node).trim() || 'Node' },
  })) as T[]
  const counts = new Map<string, number>()
  for (const node of normalized) {
    const key = nameKey(nodeReferenceName(node))
    counts.set(key, (counts.get(key) || 0) + 1)
  }

  const protectedNames = new Set(normalized
    .filter(node => counts.get(nameKey(nodeReferenceName(node))) === 1)
    .map(node => nameKey(nodeReferenceName(node))))
  const used = new Set<string>()
  const groupIndexes = new Map<string, number>()
  const renames: NodeRename[] = []
  const result = normalized.map(node => {
    const from = nodeReferenceName(node)
    const key = nameKey(from)
    let to = from
    if ((counts.get(key) || 0) > 1 || used.has(key) || RESERVED_NAMES.has(key)) {
      const stem = from.replace(/\d+$/u, '').trim() || fallbackName(node).trim() || 'Node'
      let index = groupIndexes.get(key) || 1
      while (protectedNames.has(nameKey(`${stem}${index}`)) || used.has(nameKey(`${stem}${index}`)) || RESERVED_NAMES.has(nameKey(`${stem}${index}`))) index += 1
      to = `${stem}${index}`
      groupIndexes.set(key, index + 1)
    }
    used.add(nameKey(to))
    if (from !== to) renames.push({ id: node.id, from, to })
    return from === to ? node : ({ ...node, data: { ...node.data, label: to } } as T)
  })
  return { nodes: result, renames }
}

export function rewriteNodeReferences<T>(value: T, renames: Array<Pick<NodeRename, 'from' | 'to'>>): T {
  if (!renames.length) return value
  if (Array.isArray(value)) return value.map(item => rewriteNodeReferences(item, renames)) as T
  if (value && typeof value === 'object') {
    return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, rewriteNodeReferences(item, renames)])) as T
  }
  if (typeof value !== 'string') return value
  return value.replace(/\{\{\s*([^{}]+?)\s*\}\}/gu, (token, rawPath: string) => {
    const path = rawPath.trim()
    const rename = renames.find(item => path === item.from || path.startsWith(`${item.from}.`))
    return rename ? `{{${rename.to}${path.slice(rename.from.length)}}}` : token
  }) as T
}
