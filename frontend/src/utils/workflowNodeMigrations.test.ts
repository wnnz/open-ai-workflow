import { describe, expect, it } from 'vitest'
import { migrateLegacyAnswerFillerNodes } from './workflowNodeMigrations'

describe('migrateLegacyAnswerFillerNodes', () => {
  it('moves legacy answer filling nodes to the workspace script', () => {
    const source = [
      { id: 'extract', type: 'document', data: { nodeType: 'document', config: { operation: 'extract', source: '{{inputs.file}}' } } },
      { id: 'fill', type: 'document', data: { nodeType: 'document', label: '填充答案', config: { operation: 'fill_answers', source: '{{inputs.file}}', answers: '{{llm.result}}', output_name: 'done.docx', extract_mode: 'text' } } },
    ]

    const result = migrateLegacyAnswerFillerNodes(source, {
      id: 'script-1',
      name: '英语试卷答案填充',
      input_schema: { type: 'object', properties: { source: { type: 'object', 'x-ordo-type': 'file' } } },
      output_schema: { type: 'object', properties: { file: { type: 'object', 'x-ordo-type': 'file' } } },
    })

    expect(result.migrated).toBe(true)
    expect(result.nodes[0]).toBe(source[0])
    expect(result.nodes[1]).toMatchObject({
      id: 'fill',
      type: 'script',
      data: {
        nodeType: 'script',
        label: '填充答案',
        config: {
          script_id: 'script-1',
          script_name: '英语试卷答案填充',
          version: 'latest',
          inputs: {
            source: '{{inputs.file}}',
            answers: '{{llm.result}}',
            output_name: 'done.docx',
          },
        },
      },
    })
    expect(result.nodes[1].data?.config).not.toHaveProperty('operation')
    expect(result.nodes[1].data?.config).not.toHaveProperty('extract_mode')
  })

  it('keeps the dedicated type as a compatibility fallback when the script is absent', () => {
    const source = [{ id: 'fill', type: 'document', data: { nodeType: 'document', config: { operation: 'fill_answers', source: 'file', answers: {} } } }]

    const result = migrateLegacyAnswerFillerNodes(source)

    expect(result.nodes[0].type).toBe('answer_filler')
  })

  it('replaces the legacy fixed filename with the source file stem', () => {
    const source = [{
      id: 'fill',
      type: 'answer_filler',
      data: {
        nodeType: 'answer_filler',
        config: {
          source: '{{上传英语试卷.exam_file}}',
          answers: '{{解析题目并作答.structured_output}}',
          output_name: '英语试卷_已作答.docx',
        },
      },
    }]

    const result = migrateLegacyAnswerFillerNodes(source, {
      id: 'script-1',
      name: '英语试卷答案填充',
    })

    expect((result.nodes[0].data?.config as any)?.inputs.output_name).toBe(
      '{{上传英语试卷.exam_file.stem}}_已作答.docx',
    )
  })
})
