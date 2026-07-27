// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowCommentsPanel from './WorkflowCommentsPanel.vue'

describe('WorkflowCommentsPanel', () => {
  it('submits a first comment and exposes thread actions', async () => {
    const wrapper = mount(WorkflowCommentsPanel, { props: { comments: [{ id: 'c1', position: { x: 1, y: 2 }, resolved: false, messages: [], created_at: '2026-01-01T00:00:00Z', updated_at: '2026-01-01T00:00:00Z' }], selectedId: 'c1' }, global: { plugins: [i18n] } })
    await wrapper.get('textarea').setValue('Please review')
    await wrapper.get('button.p-button').trigger('click')
    expect(wrapper.emitted('submit')?.[0]).toEqual([{ threadId: 'c1', content: 'Please review' }])
    expect(wrapper.get('button[aria-label="删除评论线程"]')).toBeTruthy()
  })
})
