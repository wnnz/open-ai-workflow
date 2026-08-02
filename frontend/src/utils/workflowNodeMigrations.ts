type WorkflowNode = {
  type?: string
  data?: {
    nodeType?: string
    config?: Record<string, any>
    [key: string]: any
  }
  [key: string]: any
}

type AnswerFillerScript = {
  id: string
  name: string
  input_schema?: Record<string, any>
  output_schema?: Record<string, any>
}

function cloneSchema(value: Record<string, any>) {
  return JSON.parse(JSON.stringify(value))
}

const LEGACY_OUTPUT_NAME = '英语试卷_已作答.docx'

function answeredOutputName(source: unknown, outputName: unknown) {
  if (outputName && outputName !== LEGACY_OUTPUT_NAME) return outputName
  const match = typeof source === 'string' ? source.match(/^\{\{\s*([^{}]+?)\s*\}\}$/) : null
  return match ? `{{${match[1].trim()}.stem}}_已作答.docx` : LEGACY_OUTPUT_NAME
}

export function migrateLegacyAnswerFillerNodes<T extends WorkflowNode>(
  nodes: T[],
  script?: AnswerFillerScript,
) {
  let migrated = false
  const migratedNodes = nodes.map(node => {
    const type = String(node.data?.nodeType || node.type || '')
    const config = node.data?.config || {}
    const legacyDocument = type === 'document' && config.operation === 'fill_answers'
    if (!legacyDocument && type !== 'answer_filler') return node
    if (type === 'answer_filler' && !script) return node

    migrated = true
    const { operation, extract_mode, page_range, ocr_fallback, ...answerConfig } = config
    void operation
    void extract_mode
    void page_range
    void ocr_fallback
    if (script) {
      const { source, answers, output_name, ...policy } = answerConfig
      return {
        ...node,
        type: 'script',
        data: {
          ...node.data,
          nodeType: 'script',
          config: {
            ...policy,
            script_id: script.id,
            script_name: script.name,
            version: 'latest',
            inputs: {
              source: source || '',
              answers: answers || '',
              output_name: answeredOutputName(source, output_name),
            },
            input_schema: cloneSchema(script.input_schema || { type: 'object', properties: {} }),
            output_schema: cloneSchema(script.output_schema || { type: 'object', properties: {} }),
          },
        },
      } as T
    }
    return {
      ...node,
      type: 'answer_filler',
      data: {
        ...node.data,
        nodeType: 'answer_filler',
        config: answerConfig,
      },
    } as T
  })

  return { nodes: migratedNodes, migrated }
}
