// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import RunHistoryPopover from './RunHistoryPopover.vue'

describe('RunHistoryPopover', () => {
  it('opens a selected run in canvas replay mode', async () => {
    const run = { id: 'run-1', status: 'succeeded', triggered_by: 'studio', created_at: '2026-07-24T12:00:00Z' }
    const wrapper = mount(RunHistoryPopover, {
      props: { open: true, runs: [run] },
      global: { plugins: [i18n] },
    })
    expect(wrapper.text()).toContain('运行历史')
    await wrapper.findAll('button').at(-1)!.trigger('click')
    expect(wrapper.emitted('replay')?.[0]).toEqual([run])
  })

  it('renders a compact full-width table and highlights the selected run when embedded', async () => {
    const run = { id: 'run-1', status: 'succeeded', triggered_by: 'form', created_at: '2026-07-24T12:00:00Z' }
    const wrapper = mount(RunHistoryPopover, {
      props: { open: true, runs: [run], embedded: true, selectedRunId: run.id },
      global: { plugins: [i18n] },
    })

    expect(wrapper.find('.surface').classes()).toContain('relative')
    expect(wrapper.find('.surface').classes()).not.toContain('absolute')
    expect(wrapper.find('.surface').classes()).not.toContain('h-full')
    expect(wrapper.find('button[aria-label="关闭"]').exists()).toBe(false)
    expect(wrapper.text()).toContain('触发方式')
    expect(wrapper.text()).toContain('运行 ID')
    expect(wrapper.text()).toContain('运行成功')
    expect(wrapper.find('button[aria-current="true"]').exists()).toBe(true)

    await wrapper.find('button[aria-label="刷新"]').trigger('click')
    expect(wrapper.emitted('refresh')).toHaveLength(1)
  })
})
