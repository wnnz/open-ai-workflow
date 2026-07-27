// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import SafeMarkdown, { renderSafeMarkdown } from './SafeMarkdown.vue'

describe('SafeMarkdown', () => {
  it('renders basic formatting and escapes raw html', () => {
    const html = renderSafeMarkdown('**Important** <script>alert(1)</script>')
    expect(html).toContain('<strong>Important</strong>')
    expect(html).toContain('&lt;script&gt;')
    expect(html).not.toContain('<script>')
  })

  it('does not create unsafe protocol links', () => {
    const wrapper = mount(SafeMarkdown, { props: { content: '[open](javascript:alert(1))' } })
    expect(wrapper.find('a').exists()).toBe(false)
    expect(wrapper.text()).toContain('open')
  })
})
