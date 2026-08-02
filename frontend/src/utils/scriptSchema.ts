export type ScriptJsonSchema = Record<string, any>

export type ScriptSchemaKind = 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array' | 'file' | 'files'

export function scriptSchemaKind(schema: ScriptJsonSchema = {}): ScriptSchemaKind {
  if (schema['x-ordo-type'] === 'file') return 'file'
  if (schema['x-ordo-type'] === 'files') return 'files'
  const type = String(schema.type || 'string')
  return ['string', 'number', 'integer', 'boolean', 'object', 'array'].includes(type)
    ? type as ScriptSchemaKind
    : 'string'
}

export function scriptSchemaForKind(kind: ScriptSchemaKind, current: ScriptJsonSchema = {}): ScriptJsonSchema {
  const description = String(current.description || '')
  if (kind === 'file') {
    return {
      type: 'object',
      'x-ordo-type': 'file',
      description,
      properties: {
        id: { type: 'string' },
        filename: { type: 'string' },
        content_type: { type: 'string' },
        size: { type: 'integer' },
      },
      required: ['filename', 'content_type'],
    }
  }
  if (kind === 'files') {
    return {
      type: 'array',
      'x-ordo-type': 'files',
      description,
      items: scriptSchemaForKind('file'),
    }
  }
  const next: ScriptJsonSchema = { type: kind, description }
  if (current.default !== undefined) next.default = current.default
  return next
}

export function workflowTypeForScriptSchema(schema: ScriptJsonSchema = {}): string {
  const kind = scriptSchemaKind(schema)
  if (kind === 'file') return 'File'
  if (kind === 'files') return 'Array[File]'
  if (kind === 'number' || kind === 'integer') return 'Number'
  if (kind === 'boolean') return 'Boolean'
  if (kind === 'object') return 'Object'
  if (kind === 'array') return 'Array'
  return 'String'
}
