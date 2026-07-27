// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowNodeSummary from './WorkflowNodeSummary.vue'

describe('WorkflowNodeSummary', () => {
  it('renders start input fields with required state and overflow count', () => {
    const wrapper = mount(WorkflowNodeSummary, {
      props: {
        nodeType: 'start',
        config: {
          input_fields: [
            { name: 'document', type: 'file', required: true },
            { name: 'language', type: 'select' },
            { name: 'notes', type: 'textarea' },
            { name: 'copies', type: 'number' },
          ],
        },
      },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('document')
    expect(wrapper.text()).toContain('必填')
    expect(wrapper.text()).toContain('+1')
    expect(wrapper.text()).not.toContain('copies')
  })

  it('renders structured end outputs', () => {
    const wrapper = mount(WorkflowNodeSummary, {
      props: { nodeType: 'end', config: { outputs: [{ name: 'answer', type: 'String' }] } },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('answer')
    expect(wrapper.text()).toContain('String')
  })

  it('renders model and HTTP summaries', async () => {
    const wrapper = mount(WorkflowNodeSummary, {
      props: { nodeType: 'llm', config: { model: 'gpt-5.6-sol' } },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('gpt-5.6-sol')
    await wrapper.setProps({ nodeType: 'http', config: { method: 'post', url: 'https://api.example.com/jobs' } })
    expect(wrapper.text()).toContain('POST')
    expect(wrapper.text()).toContain('api.example.com/jobs')
  })
})
