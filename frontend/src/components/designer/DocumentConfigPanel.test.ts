// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import DocumentConfigPanel from './DocumentConfigPanel.vue'

function mountPanel(config: Record<string, unknown>) {
  return mount(DocumentConfigPanel, {
    props: { config, variableGroups: [] },
    global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
  })
}

describe('DocumentConfigPanel', () => {
  it('shows the source document input for extraction', () => {
    const wrapper = mountPanel({ operation: 'extract', source: '{{上传英语试卷.exam_file}}' })

    expect(wrapper.find('[data-testid="document-config-panel"]').exists()).toBe(true)
    expect(wrapper.text()).toContain('来源文件或变量')
    expect(wrapper.findAll('input.variable-control')).toHaveLength(1)
    expect((wrapper.get('input.variable-control').element as HTMLInputElement).value).toBe('{{上传英语试卷.exam_file}}')
  })

  it('shows source and answer-plan inputs when filling answers', () => {
    const wrapper = mountPanel({ operation: 'fill_answers' })

    expect(wrapper.text()).toContain('来源文件或变量')
    expect(wrapper.text()).toContain('答案方案或变量')
    expect(wrapper.findAll('input.variable-control')).toHaveLength(2)
    expect(wrapper.find('details').exists()).toBe(false)
    expect(wrapper.findAll('[data-section-kind]').map(section => section.attributes('data-section-kind'))).toEqual(['parameters', 'input'])
  })
})
