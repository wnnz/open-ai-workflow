// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import PrimeVue from 'primevue/config'
import { i18n } from '@/i18n'
import WorkflowEnvironmentPanel from './WorkflowEnvironmentPanel.vue'

describe('WorkflowEnvironmentPanel', () => {
  it('masks secret values and opens the variable editor', async () => {
    Object.assign(navigator, { clipboard: { writeText: vi.fn() } })
    const wrapper = mount(WorkflowEnvironmentPanel, { props: { variables: [{ id: 'v1', name: 'API_KEY', value_type: 'secret', value: '••••••••', has_value: true, description: 'Provider key' }] }, global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] }, attachTo: document.body })
    expect(wrapper.text()).not.toContain('real-secret')
    expect(wrapper.text()).toContain('••••••••')
    await wrapper.get('button[aria-label="编辑"]').trigger('click')
    expect(document.body.textContent).toContain('编辑环境变量')
    wrapper.unmount()
  })
})
