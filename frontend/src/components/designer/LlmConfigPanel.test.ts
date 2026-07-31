// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import LlmConfigPanel from './LlmConfigPanel.vue'

describe('LlmConfigPanel', () => {
  it('separates parameters from every variable-backed input', () => {
    const wrapper = mount(LlmConfigPanel, {
      props: {
        config: {
          provider_id: 'provider-1', model: 'gpt-test', context: '{{start.text}}',
          messages: [{ role: 'user', content: '{{start.question}}' }],
          vision: { enabled: true, variable: '{{extract.images}}', detail: 'high' },
          reasoning: { separate: false }, temperature: 0.1, top_p: 1, max_tokens: 1000,
          response_format: 'text',
        },
        providers: [{ id: 'provider-1', name: 'Provider', default_model: 'gpt-test' }],
        variableGroups: [], buffers: { llmSchema: '{}' }, errors: {},
      },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })

    const parameters = wrapper.get('[data-section-kind="parameters"]')
    const inputs = wrapper.get('[data-section-kind="input"]')
    expect(parameters.element.compareDocumentPosition(inputs.element) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy()
    expect(inputs.text()).toContain('上下文')
    expect(inputs.text()).toContain('提示词消息')
    expect(inputs.text()).toContain('图片变量')
    expect(inputs.findAll('.variable-control')).toHaveLength(3)
    expect(wrapper.find('details').exists()).toBe(false)
  })
})
