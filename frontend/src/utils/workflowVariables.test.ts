import { describe, expect, it } from 'vitest'
import { buildAllVariableCatalog, buildVariableCatalog, getNodeOutputVariables, readRuntimeVariable } from './workflowVariables'

const nodes = [
  { id: 'start', type: 'start', position: { x: 0, y: 0 }, data: { nodeType: 'start', label: '用户输入', config: { input_fields: [
    { name: 'message', label: '问题', type: 'text' },
    { name: 'files', label: '附件', type: 'files' },
  ] } } },
  { id: 'extract-1', type: 'extract', position: { x: 0, y: 0 }, data: { nodeType: 'extract', label: '参数提取', config: { fields: [{ name: 'customer' }, { name: 'count', type: 'Number' }] } } },
  { id: 'variables-1', type: 'variable', position: { x: 0, y: 0 }, data: { nodeType: 'variable', label: '变量赋值', config: { values: { region: 'SG', active: true } } } },
  { id: 'llm-1', type: 'llm', position: { x: 0, y: 0 }, data: { nodeType: 'llm', label: '生成内容', config: { response_format: 'json_schema', response_schema: { type: 'object', properties: { title: { type: 'string' } } } } } },
  { id: 'target', type: 'template', position: { x: 0, y: 0 }, data: { nodeType: 'template', label: '模板', config: {} } },
  { id: 'unrelated', type: 'http', position: { x: 0, y: 0 }, data: { nodeType: 'http', label: '其他请求', config: {} } },
]

describe('workflow variable catalog', () => {
  it('lists only transitive upstream variables using runtime paths', () => {
    const groups = buildVariableCatalog(nodes, [
      { source: 'start', target: 'extract-1' },
      { source: 'extract-1', target: 'variables-1' },
      { source: 'variables-1', target: 'llm-1' },
      { source: 'llm-1', target: 'target' },
    ], 'target')

    expect(groups.map(group => group.nodeId)).toEqual(['start', 'extract-1', 'variables-1', 'llm-1'])
    expect(groups.flatMap(group => group.variables)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: '用户输入.message', label: '问题', type: 'String' }),
      expect.objectContaining({ path: '用户输入.files', type: 'Array[File]' }),
      expect.objectContaining({ path: '参数提取.customer' }),
      expect.objectContaining({ path: '变量赋值.region' }),
      expect.objectContaining({ path: '生成内容.text' }),
      expect.objectContaining({ path: '生成内容.structured_output.title', label: 'title', type: 'string' }),
    ]))
    expect(groups.some(group => group.nodeId === 'unrelated')).toBe(false)
    expect(groups.some(group => group.nodeId === 'target')).toBe(false)
  })

  it('returns no variables for an unconnected node', () => {
    expect(buildVariableCatalog(nodes, [], 'target')).toEqual([])
  })

  it('builds a whole-graph catalog and resolves runtime values', () => {
    const catalog = buildAllVariableCatalog(nodes)
    expect(catalog.map(group => group.nodeId)).toEqual(expect.arrayContaining(['start', 'extract-1', 'variables-1', 'llm-1', 'unrelated']))
    const httpVariables = catalog.find(group => group.nodeId === 'unrelated')!.variables
    expect(httpVariables).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: '其他请求.status_code', type: 'Number' }),
      expect.objectContaining({ path: '其他请求.elapsed_ms', type: 'Number' }),
      expect.objectContaining({ path: '其他请求.ok', type: 'Boolean' }),
    ]))
    const results = {
      start: { node_type: 'start', output: { message: 'Hello' } },
      'llm-1': { node_type: 'llm', output: { structured_output: { title: 'Weekly report' } } },
    }
    expect(readRuntimeVariable('用户输入.message', results, nodes)).toBe('Hello')
    expect(readRuntimeVariable('生成内容.structured_output.title', results, nodes)).toBe('Weekly report')
    expect(readRuntimeVariable('生成内容.structured_output.missing', results, nodes)).toBeUndefined()
    expect(readRuntimeVariable('llm-1.structured_output.title', results, nodes)).toBe('Weekly report')
  })

  it('exposes condition results and error-branch outputs for dynamic nodes', () => {
    const condition = { id: 'condition-1', type: 'condition', position: { x: 0, y: 0 }, data: { nodeType: 'condition', config: {} } }
    expect(getNodeOutputVariables(condition)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: 'condition-1.result', type: 'Boolean' }),
      expect.objectContaining({ path: 'condition-1.branch', type: 'String' }),
      expect.objectContaining({ path: 'condition-1.clauses', type: 'Array[Boolean]' }),
    ]))

    const structuredLlm = {
      ...nodes.find(node => node.id === 'llm-1')!,
      data: {
        ...nodes.find(node => node.id === 'llm-1')!.data,
        config: { ...nodes.find(node => node.id === 'llm-1')!.data.config, error_strategy: 'error_branch' },
      },
    }
    expect(getNodeOutputVariables(structuredLlm)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: '生成内容.structured_output.title' }),
      expect.objectContaining({ path: '生成内容.error_type' }),
      expect.objectContaining({ path: '生成内容.error_message' }),
    ]))

    const reasoningLlm = {
      ...structuredLlm,
      data: { ...structuredLlm.data, config: { ...structuredLlm.data.config, reasoning: { separate: true } } },
    }
    expect(getNodeOutputVariables(reasoningLlm)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: '生成内容.reasoning_content', type: 'String' }),
    ]))
  })

  it('exposes operation-specific document outputs', () => {
    const document = (operation: string) => ({ id: 'document-1', type: 'document', position: { x: 0, y: 0 }, data: { nodeType: 'document', config: { operation } } })
    expect(getNodeOutputVariables(document('extract'))).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: 'document-1.content', type: 'String' }),
      expect.objectContaining({ path: 'document-1.tables', type: 'Array[Object]' }),
    ]))
    expect(getNodeOutputVariables(document('split'))).toEqual([
      expect.objectContaining({ path: 'document-1.files', type: 'Array[File]' }),
    ])
    expect(getNodeOutputVariables(document('ocr'))).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: 'document-1.text', type: 'String' }),
      expect.objectContaining({ path: 'document-1.blocks', type: 'Array[Object]' }),
    ]))
  })

  it('exposes simple and grouped aggregation outputs', () => {
    const simple = { id: 'aggregate-1', type: 'aggregate', position: { x: 0, y: 0 }, data: { nodeType: 'aggregate', config: { variables: ['{{a.value}}'] } } }
    expect(getNodeOutputVariables(simple)).toEqual([expect.objectContaining({ path: 'aggregate-1.output', type: 'Any' })])

    const grouped = { id: 'aggregate-2', type: 'aggregate', position: { x: 0, y: 0 }, data: { nodeType: 'aggregate', config: { group_enabled: true, groups: [{ name: 'answer', variables: ['{{a.value}}'] }, { name: 'file', variables: ['{{b.file}}'] }] } } }
    expect(getNodeOutputVariables(grouped)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: 'aggregate-2.answer', type: 'Any' }),
      expect.objectContaining({ path: 'aggregate-2.file', type: 'Any' }),
    ]))
  })

  it('exposes structured variable assignments and both list outputs', () => {
    const variable = { id: 'variable-2', type: 'variable', position: { x: 0, y: 0 }, data: { nodeType: 'variable', config: { assignments: [{ name: 'total', type: 'Number', value: 3 }] } } }
    const list = { id: 'list-1', type: 'list', position: { x: 0, y: 0 }, data: { nodeType: 'list', config: {} } }
    expect(getNodeOutputVariables(variable)).toEqual([expect.objectContaining({ path: 'variable-2.total', type: 'Number' })])
    expect(getNodeOutputVariables(list)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: 'list-1.items', type: 'Array' }),
      expect.objectContaining({ path: 'list-1.item', type: 'Any' }),
    ]))
  })

  it('exposes declared inline-code outputs and runtime metadata', () => {
    const code = { id: 'code-1', type: 'code', position: { x: 0, y: 0 }, data: { nodeType: 'code', config: { outputs: [{ name: 'answer', type: 'String' }, { name: 'score', type: 'Number' }] } } }
    expect(getNodeOutputVariables(code)).toEqual(expect.arrayContaining([
      expect.objectContaining({ path: 'code-1.answer', type: 'String' }),
      expect.objectContaining({ path: 'code-1.score', type: 'Number' }),
      expect.objectContaining({ path: 'code-1._logs', type: 'Array[String]' }),
      expect.objectContaining({ path: 'code-1._elapsed_ms', type: 'Number' }),
    ]))
  })
})
