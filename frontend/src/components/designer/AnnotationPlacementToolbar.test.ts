// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import AnnotationPlacementToolbar from './AnnotationPlacementToolbar.vue'

describe('AnnotationPlacementToolbar', () => {
  it('changes annotation color and cancels placement', async () => {
    const wrapper = mount(AnnotationPlacementToolbar, { props: { color: 'yellow' }, global: { plugins: [i18n] } })
    await wrapper.get('button[aria-label="蓝色"]').trigger('click')
    await wrapper.get('button[aria-label="关闭"]').trigger('click')
    expect(wrapper.emitted('update:color')?.[0]).toEqual(['blue'])
    expect(wrapper.emitted('cancel')).toHaveLength(1)
  })
})
