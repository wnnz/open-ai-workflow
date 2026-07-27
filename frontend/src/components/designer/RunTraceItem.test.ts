// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import RunTraceItem from './RunTraceItem.vue'

describe('RunTraceItem', () => {
  it('expands trace input, output, and metadata and focuses the node', async () => {
    const wrapper = mount(RunTraceItem, {
      props: { label: '内容生成', item: { node_id: 'llm-1', node_type: 'llm', status: 'succeeded', attempts: 1, input: { prompt: 'hello' }, output: { text: 'world' }, metadata: { duration_ms: 1250, usage: { total_tokens: 20 } } } },
      global: { plugins: [i18n] },
    })
    expect(wrapper.text()).toContain('内容生成')
    expect(wrapper.text()).toContain('1.25 s')
    await wrapper.get('button[aria-expanded="false"]').trigger('click')
    expect(wrapper.text()).toContain('hello')
    expect(wrapper.text()).toContain('world')
    expect(wrapper.text()).toContain('total_tokens')
    await wrapper.get('button[title="聚焦画布节点"]').trigger('click')
    expect(wrapper.emitted('focus')?.[0]).toEqual(['llm-1'])
  })
})
