// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowRunLogsPanel from './WorkflowRunLogsPanel.vue'

describe('WorkflowRunLogsPanel', () => {
  it('embeds run history and forwards the selected run for replay', async () => {
    const run = { id: 'run-1', status: 'succeeded', triggered_by: 'form', created_at: '2026-07-31T08:15:17Z' }
    const wrapper = mount(WorkflowRunLogsPanel, {
      props: { runs: [run], detailOpen: true, selectedRunId: run.id },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('运行历史')
    expect(wrapper.find('.surface').classes()).toContain('relative')
    expect(wrapper.find('section').classes()).toContain('xl:pr-[458px]')
    expect(wrapper.find('button[aria-current="true"]').exists()).toBe(true)

    await wrapper.findAll('button').at(-1)!.trigger('click')
    expect(wrapper.emitted('replay')?.[0]).toEqual([run])
  })
})
