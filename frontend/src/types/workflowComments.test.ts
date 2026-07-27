import { describe, expect, it } from 'vitest'
import { normalizeWorkflowComments } from './workflowComments'

describe('normalizeWorkflowComments', () => {
  it('keeps valid anchored threads and removes empty messages', () => {
    const comments = normalizeWorkflowComments([{ id: 'c1', position: { x: 12, y: 34 }, resolved: true, messages: [
      { id: 'm1', author_name: 'A', content: '  Review this  ' },
      { id: 'm2', content: '   ' },
    ] }])
    expect(comments).toHaveLength(1)
    expect(comments[0]).toMatchObject({ id: 'c1', position: { x: 12, y: 34 }, resolved: true })
    expect(comments[0].messages).toHaveLength(1)
    expect(comments[0].messages[0].content).toBe('Review this')
  })

  it('rejects malformed anchors', () => {
    expect(normalizeWorkflowComments([{ id: 'bad', position: { x: 'x', y: 1 } }, null])).toEqual([])
  })
})

