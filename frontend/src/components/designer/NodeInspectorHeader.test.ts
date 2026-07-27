// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import NodeInspectorHeader from './NodeInspectorHeader.vue'

describe('NodeInspectorHeader', () => {
  it('edits metadata and exposes node actions', async () => {
    const node = { id: 'llm-1', data: { label: 'LLM', description: 'Answer questions' } }
    const wrapper = mount(NodeInspectorHeader, { props: { node, nodeType: 'llm' }, global: { plugins: [i18n] } })
    await wrapper.get('input[aria-label="编辑节点标题"]').setValue('智能问答')
    await wrapper.get('input[aria-label="编辑节点描述"]').setValue('根据资料回答')
    await wrapper.get('button[aria-label="运行此步骤"]').trigger('click')
    expect(wrapper.emitted('update:label')?.at(-1)).toEqual(['智能问答'])
    expect(wrapper.emitted('update:description')?.at(-1)).toEqual(['根据资料回答'])
    expect(wrapper.emitted('run')).toHaveLength(1)
  })
})
