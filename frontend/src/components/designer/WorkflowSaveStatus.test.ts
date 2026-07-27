// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowSaveStatus from './WorkflowSaveStatus.vue'

describe('WorkflowSaveStatus', () => {
  it('shows saving and saved states', async () => {
    const wrapper = mount(WorkflowSaveStatus, { props: { state: 'saving' }, global: { plugins: [i18n] } })
    expect(wrapper.text()).toContain('正在保存')
    await wrapper.setProps({ state: 'saved', savedAt: new Date('2026-07-25T08:30:00') })
    expect(wrapper.text()).toContain('自动保存')
    expect(wrapper.text()).toContain('08:30')
  })

  it('offers retry after a save failure', async () => {
    const wrapper = mount(WorkflowSaveStatus, { props: { state: 'error', error: 'network unavailable' }, global: { plugins: [i18n] } })
    expect(wrapper.get('[role="status"]').attributes('title')).toBeUndefined()
    expect(wrapper.text()).toContain('保存失败')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('retry')).toHaveLength(1)
  })

  it('offers a reload action for version conflicts', async () => {
    const wrapper = mount(WorkflowSaveStatus, { props: { state: 'conflict', error: 'conflict' }, global: { plugins: [i18n] } })
    expect(wrapper.text()).toContain('版本冲突')
    await wrapper.get('button').trigger('click')
    expect(wrapper.emitted('reload')).toHaveLength(1)
  })
})
