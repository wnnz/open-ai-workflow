// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import MarkdownComposer from './MarkdownComposer.vue'

describe('MarkdownComposer', () => {
  it('wraps the selected text with markdown syntax', async () => {
    const wrapper = mount(MarkdownComposer, { props: { modelValue: 'Please review' }, global: { plugins: [i18n] } })
    const textarea = wrapper.get('textarea').element
    textarea.setSelectionRange(7, 13)
    await wrapper.get('button[aria-label="加粗（Ctrl+B）"]').trigger('click')
    expect(wrapper.emitted('update:modelValue')?.at(-1)).toEqual(['Please **review**'])
  })

  it('emits submit on Ctrl+Enter', async () => {
    const wrapper = mount(MarkdownComposer, { props: { modelValue: 'Ready' }, global: { plugins: [i18n] } })
    await wrapper.get('textarea').trigger('keydown', { key: 'Enter', ctrlKey: true })
    expect(wrapper.emitted('submit')).toHaveLength(1)
  })
})
