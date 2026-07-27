// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import AgentConfigPanel from './AgentConfigPanel.vue'

describe('AgentConfigPanel', () => {
  it('adds a workspace script as an agent tool', async () => {
    const config: any = { provider_id: '', model: '', instructions: '', max_iterations: 5 }
    const wrapper = mount(AgentConfigPanel, { props: { config, providers: [], scripts: [{ id: 's1', name: 'Search Script' }], datasets: [], variableGroups: [] }, global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] } })
    const selects = wrapper.findAll('select')
    await selects[1].setValue('script:s1')
    await wrapper.get('button[aria-label="添加工具"]').trigger('click')
    expect(config.tools).toMatchObject([{ type: 'script', reference_id: 's1', name: 'Search Script', enabled: true }])
  })
})
