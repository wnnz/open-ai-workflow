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
})
