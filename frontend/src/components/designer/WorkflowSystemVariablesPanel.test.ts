// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowSystemVariablesPanel from './WorkflowSystemVariablesPanel.vue'

describe('WorkflowSystemVariablesPanel', () => {
  it('lists all runtime variables and copies an insertion token', async () => {
    const writeText = vi.fn()
    Object.assign(navigator, { clipboard: { writeText } })
    const wrapper = mount(WorkflowSystemVariablesPanel, { global: { plugins: [i18n] } })
    expect(wrapper.text()).toContain('sys.workflow_run_id')
    await wrapper.get('button[aria-label="复制系统变量 workflow_id"]').trigger('click')
    expect(writeText).toHaveBeenCalledWith('{{sys.workflow_id}}')
  })
})
