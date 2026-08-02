// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { i18n } from '@/i18n'
import api from '@/api/client'
import ScriptConfigPanel from './ScriptConfigPanel.vue'

vi.mock('@/api/client', () => ({ default: { get: vi.fn() } }))

describe('ScriptConfigPanel', () => {
  beforeEach(() => {
    vi.mocked(api.get).mockImplementation(async (url: string) => {
      if (url.endsWith('/versions')) return { data: { items: [{ version: 2, entrypoint: 'main:main' }], total: 1 } } as any
      return { data: {
        input_schema: { type: 'object', properties: { text: { type: 'string', description: 'Text to process' } }, required: ['text'] },
        output_schema: { type: 'object', properties: { result: { type: 'string' } } },
      } } as any
    })
  })

  it('builds workflow input mappings from the selected script schema', async () => {
    const config: any = { script_id: 'script-1', version: 'latest', inputs: {} }
    const wrapper = mount(ScriptConfigPanel, {
      props: { config, scripts: [{ id: 'script-1', name: 'Formatter', latest_version: 2 }], workspaceId: 'workspace-1', variableGroups: [] },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })
    await flushPromises()

    expect(config.inputs).toHaveProperty('text', '')
    expect(wrapper.text()).toContain('脚本配置')
    expect(wrapper.text().match(/工作区脚本/g)).toHaveLength(1)
    expect(wrapper.text()).toContain('Text to process')
    const outputSection = wrapper.findAll('[data-section-kind="default"]').find(section => section.text().includes('输出'))
    expect(outputSection).toBeTruthy()
    await outputSection!.get('button[aria-expanded="false"]').trigger('click')
    expect(wrapper.text()).toContain('result')
  })
})
