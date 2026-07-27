// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import ToggleSwitch from './ToggleSwitch.vue'

describe('ToggleSwitch', () => {
  it('keeps the enabled thumb inside the track', () => {
    const wrapper = mount(ToggleSwitch, { props: { modelValue: true, label: 'Retry' } })
    const thumb = wrapper.get('span')

    expect(thumb.classes()).toContain('left-0')
    expect(thumb.classes()).toContain('translate-x-[18px]')
    expect(wrapper.get('button').attributes('aria-checked')).toBe('true')
  })
})
