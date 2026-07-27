// @vitest-environment jsdom
import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import WorkflowCommentPin from './WorkflowCommentPin.vue'

describe('WorkflowCommentPin', () => {
  it('shows the number of messages in the thread', () => {
    const wrapper = mount(WorkflowCommentPin, { props: { count: 2, label: '评论 1' } })
    expect(wrapper.text()).toBe('2')
  })
})
