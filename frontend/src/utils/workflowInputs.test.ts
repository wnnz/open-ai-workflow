import { describe, expect, it } from 'vitest'
import { coerceWorkflowInputValues, createWorkflowInputValues } from './workflowInputs'

describe('workflow input values', () => {
  const fields = [
    { name: 'topic', type: 'text' as const, default_value: 'Weekly report' },
    { name: 'tone', type: 'select' as const, default_value: 'Formal' },
    { name: 'count', type: 'number' as const, default_value: 3 },
    { name: 'attachment', type: 'file' as const },
    { name: 'references', type: 'files' as const },
  ]

  it('initializes defaults and file values', () => {
    expect(createWorkflowInputValues(fields)).toEqual({
      topic: 'Weekly report', tone: 'Formal', count: 3, attachment: null, references: [],
    })
  })

  it('coerces only numeric inputs', () => {
    expect(coerceWorkflowInputValues(fields, { topic: '42', tone: 'Formal', count: '7' })).toEqual({
      topic: '42', tone: 'Formal', count: 7,
    })
  })
})
