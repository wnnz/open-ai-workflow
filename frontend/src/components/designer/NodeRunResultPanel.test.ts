// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import NodeRunResultPanel from './NodeRunResultPanel.vue'

describe('NodeRunResultPanel', () => {
  it('shows output and lets the user inspect resolved input', async () => {
    const result = { node_id: 'template-1', node_type: 'template', status: 'succeeded', input: { name: 'Codex' }, output: { result: 'Hello Codex' }, metadata: { executor: 'built-in', input_bytes: 16, output_bytes: 24, retry_count: 0, usage: { input_tokens: 4, output_tokens: 2, total_tokens: 6 }, logs: ['rendered template'] }, attempts: 1, started_at: '2026-01-01T00:00:00.000Z', finished_at: '2026-01-01T00:00:00.125Z' }
    const wrapper = mount(NodeRunResultPanel, { props: { result }, global: { plugins: [i18n] } })
    expect(wrapper.text()).toContain('Hello Codex')
    expect(wrapper.text()).toContain('125 ms')
    await wrapper.get('button:nth-of-type(1)').trigger('click')
    expect(wrapper.text()).toContain('Codex')
    await wrapper.findAll('button').find(button => button.text().includes('数据处理'))!.trigger('click')
    expect(wrapper.text()).toContain('rendered template')
    expect(wrapper.text()).toContain('6 Tokens')
  })

  it('shows an empty state without a trace', () => {
    const wrapper = mount(NodeRunResultPanel, { props: { result: null }, global: { plugins: [i18n] } })
    expect(wrapper.text()).toContain('暂时没有运行记录')
  })
})
