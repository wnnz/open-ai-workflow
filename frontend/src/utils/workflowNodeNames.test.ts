import { describe, expect, it } from 'vitest'
import { allocateDefaultNodeName, ensureUniqueNodeNames, nextUniqueNodeName, rewriteNodeReferences, validateNodeName } from './workflowNodeNames'

const node = (id: string, type: string, label: string) => ({ id, type, position: { x: 0, y: 0 }, data: { nodeType: type, label, config: {} } })

describe('workflow node names', () => {
  it('numbers both default nodes when a second node of the same type is added', () => {
    const nodes = [node('llm-a', 'llm', '大模型')]
    expect(allocateDefaultNodeName(nodes, 'llm', '大模型')).toEqual({
      name: '大模型2',
      renames: [{ id: 'llm-a', from: '大模型', to: '大模型1' }],
    })
  })

  it('normalizes duplicate legacy names and preserves unique names', () => {
    const result = ensureUniqueNodeNames([
      node('llm-a', 'llm', '大模型'),
      node('llm-b', 'llm', '大模型'),
      node('custom', 'template', '自定义'),
    ], item => item.type || 'Node')
    expect(result.nodes.map(item => item.data.label)).toEqual(['大模型1', '大模型2', '自定义'])
  })

  it('rejects ambiguous names and allocates unique copy names', () => {
    const nodes = [node('a', 'llm', '大模型1'), node('b', 'template', '模板')]
    expect(validateNodeName(nodes, 'b', '大模型1')).toBe('duplicate')
    expect(validateNodeName(nodes, 'b', 'env')).toBe('reserved')
    expect(validateNodeName(nodes, 'b', '错误.名称')).toBe('invalid')
    expect(nextUniqueNodeName(nodes, '大模型1')).toBe('大模型2')
  })

  it('rewrites nested mustache references without touching unrelated template bindings', () => {
    const config = {
      prompt: '总结 {{大模型.text}}',
      nested: [{ value: '{{ 大模型.structured_output.title }}' }],
      template: 'Hello {{ name }}',
    }
    expect(rewriteNodeReferences(config, [{ from: '大模型', to: '大模型1' }])).toEqual({
      prompt: '总结 {{大模型1.text}}',
      nested: [{ value: '{{大模型1.structured_output.title}}' }],
      template: 'Hello {{ name }}',
    })
  })
})
