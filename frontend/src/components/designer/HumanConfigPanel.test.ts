// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import HumanConfigPanel from './HumanConfigPanel.vue'

describe('HumanConfigPanel', () => {
  it('renders the complete approval configuration', () => {
    const wrapper = mount(HumanConfigPanel, {
      props: {
        variableGroups: [],
        config: {
          submission_methods: ['studio'],
          form_content: 'Please review',
          actions: [
            { id: 'approve', label: 'Approve', value: 'approved', style: 'primary' },
            { id: 'reject', label: 'Reject', value: 'rejected', style: 'danger' },
          ],
          timeout_minutes: 4320,
        },
      },
      global: {
        plugins: [i18n],
        stubs: { InputText: true, Select: true },
      },
    })
    expect(wrapper.text()).toContain('提交方式')
    expect(wrapper.text()).toContain('表单内容')
    expect(wrapper.text()).toContain('用户操作')
    expect(wrapper.text()).toContain('超时设置')
  })
})
