export interface WorkflowCommentMessage {
  id: string
  author_id: string
  author_name: string
  content: string
  created_at: string
}

export interface WorkflowCommentThread {
  id: string
  position: { x: number; y: number }
  resolved: boolean
  messages: WorkflowCommentMessage[]
  created_at: string
  updated_at: string
}

export function normalizeWorkflowComments(value: unknown): WorkflowCommentThread[] {
  if (!Array.isArray(value)) return []
  return value.flatMap((item: any) => {
    if (!item || typeof item !== 'object' || !item.id || !Number.isFinite(item.position?.x) || !Number.isFinite(item.position?.y)) return []
    const createdAt = String(item.created_at || new Date().toISOString())
    const messages = Array.isArray(item.messages) ? item.messages.flatMap((message: any) => {
      if (!message || typeof message.content !== 'string' || !message.content.trim()) return []
      return [{
        id: String(message.id || crypto.randomUUID()),
        author_id: String(message.author_id || ''),
        author_name: String(message.author_name || 'User'),
        content: message.content.trim(),
        created_at: String(message.created_at || createdAt),
      }]
    }) : []
    return [{
      id: String(item.id),
      position: { x: Number(item.position.x), y: Number(item.position.y) },
      resolved: Boolean(item.resolved),
      messages,
      created_at: createdAt,
      updated_at: String(item.updated_at || createdAt),
    }]
  })
}

