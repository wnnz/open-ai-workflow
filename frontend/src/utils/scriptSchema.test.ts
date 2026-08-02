import { describe, expect, it } from 'vitest'
import { scriptSchemaForKind, scriptSchemaKind, workflowTypeForScriptSchema } from './scriptSchema'

describe('script schema types', () => {
  it('round-trips semantic file types through JSON Schema extensions', () => {
    const file = scriptSchemaForKind('file', { description: 'Source document' })
    const files = scriptSchemaForKind('files')

    expect(scriptSchemaKind(file)).toBe('file')
    expect(workflowTypeForScriptSchema(file)).toBe('File')
    expect(file).toMatchObject({ type: 'object', 'x-ordo-type': 'file', description: 'Source document' })
    expect(scriptSchemaKind(files)).toBe('files')
    expect(workflowTypeForScriptSchema(files)).toBe('Array[File]')
  })

  it('maps scalar JSON Schema types to workflow variable types', () => {
    expect(workflowTypeForScriptSchema({ type: 'integer' })).toBe('Number')
    expect(workflowTypeForScriptSchema({ type: 'boolean' })).toBe('Boolean')
    expect(workflowTypeForScriptSchema({ type: 'object' })).toBe('Object')
  })
})
