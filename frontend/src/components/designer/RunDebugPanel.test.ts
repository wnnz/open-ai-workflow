// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import RunDebugPanel from './RunDebugPanel.vue'

describe('RunDebugPanel', () => {
  it('keeps input, output, detail and trace in one side panel', async () => {
    const wrapper = mount(RunDebugPanel, {
      props: {
        open: true,
        title: 'Test Run',
        fields: [{ name: 'message', label: 'Message', type: 'text' }],
        inputs: { message: 'hello' },
        uploadingField: '',
        result: {
          id: 'run-1',
          status: 'succeeded',
          inputs: { message: 'hello' },
          outputs: { message: 'hello' },
          trace: [{ node_id: 'start', node_type: 'start', status: 'succeeded', output: { message: 'hello' }, attempts: 1 }],
        },
        error: '',
        running: false,
        nodeLabels: { start: '开始' },
      },
      global: {
        plugins: [i18n],
        stubs: {
          WorkflowInputField: { template: '<div>Message field</div>' },
          Button: { template: '<button type="submit"><slot /></button>' },
          AlertBanner: true,
        },
      },
    })
    expect(wrapper.text()).toContain('输入')
    expect(wrapper.text()).toContain('输出')
    expect(wrapper.text()).toContain('运行详情')
    expect(wrapper.text()).toContain('节点轨迹')
    await wrapper.get('form').trigger('submit')
    expect(wrapper.emitted('run')).toHaveLength(1)

    await wrapper.findAll('nav button').find(button => button.text().includes('节点轨迹'))!.trigger('click')
    expect(wrapper.text()).toContain('开始')
    await wrapper.get('button[title="聚焦画布节点"]').trigger('click')
    expect(wrapper.emitted('focusNode')).toEqual([['start']])
  })

  it('locks historical replay to result, detail and trace tabs', () => {
    const wrapper = mount(RunDebugPanel, {
      props: {
        open: true,
        title: 'Historical Run',
        fields: [],
        inputs: {},
        uploadingField: '',
        result: { id: 'run-2', status: 'succeeded', outputs: {}, trace: [] },
        error: '',
        running: false,
        readonly: true,
      },
      global: { plugins: [i18n], stubs: { Button: true, AlertBanner: true } },
    })
    expect(wrapper.text()).toContain('正在查看历史运行')
    expect(wrapper.find('form').exists()).toBe(false)
    expect(wrapper.findAll('nav button')).toHaveLength(3)
  })

  it('offers cancellation for an active run and retry for a completed run', async () => {
    const wrapper = mount(RunDebugPanel, {
      props: {
        open: true,
        title: 'Controlled Run',
        fields: [],
        inputs: {},
        uploadingField: '',
        result: { id: 'run-3', status: 'running', outputs: {}, trace: [] },
        error: '',
        running: true,
      },
      global: { plugins: [i18n], stubs: { AlertBanner: true } },
    })
    const cancel = wrapper.findAll('button').find(button => button.text().includes('停止运行'))
    expect(cancel).toBeTruthy()
    await cancel!.trigger('click')
    expect(wrapper.emitted('cancel')).toHaveLength(1)

    await wrapper.setProps({ result: { id: 'run-3', status: 'failed', outputs: {}, trace: [] }, running: false })
    await wrapper.findAll('nav button').find(button => button.text().includes('输出'))!.trigger('click')
    const retry = wrapper.findAll('button').find(button => button.text().includes('重新运行'))
    expect(retry).toBeTruthy()
    await retry!.trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })
})
