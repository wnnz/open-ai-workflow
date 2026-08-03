// @vitest-environment jsdom

import { mount, type VueWrapper } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PrimeVue from 'primevue/config'
import { i18n } from '@/i18n'
import WorkflowSettingsPanel from './WorkflowSettingsPanel.vue'

describe('WorkflowSettingsPanel', () => {
  it('validates and saves a custom published slug', async () => {
    let wrapper: VueWrapper
    wrapper = mount(WorkflowSettingsPanel, {
      props: {
        modelValue: 'workspace-a1b2c3',
        savedSlug: 'workspace-a1b2c3',
        origin: 'https://example.com',
        published: true,
        'onUpdate:modelValue': value => wrapper.setProps({ modelValue: value }),
      },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })

    expect(wrapper.text()).toContain('公开地址')
    expect(wrapper.text()).toContain('https://example.com/apps/workspace-a1b2c3')
    expect(wrapper.text()).toContain('旧的 Web、API 和 Webhook 地址会立即失效')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()

    const input = wrapper.get('input')
    await input.setValue('Invalid Slug')
    await wrapper.vm.$nextTick()
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['invalid slug'])
    expect(wrapper.text()).toContain('只能使用小写字母、数字和单个连字符')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeDefined()

    await input.setValue('english-exam-answer-filler')
    await wrapper.vm.$nextTick()
    expect(wrapper.text()).toContain('https://example.com/apps/english-exam-answer-filler')
    expect(wrapper.get('button[type="submit"]').attributes('disabled')).toBeUndefined()
    await wrapper.get('form').trigger('submit')

    expect(wrapper.emitted('save')).toHaveLength(1)
  })

  it('does not offer a public link before publication', () => {
    const wrapper = mount(WorkflowSettingsPanel, {
      props: {
        modelValue: 'draft-workflow',
        savedSlug: 'draft-workflow',
        origin: 'https://example.com',
      },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })

    expect(wrapper.find('a[href="https://example.com/apps/draft-workflow"]').exists()).toBe(false)
  })
})
