// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowApiPanel from './WorkflowApiPanel.vue'

const mountPanel = (triggers: string[], inputFields: Array<{ type?: string }> = []) => mount(WorkflowApiPanel, {
  props: { origin: 'https://example.com', slug: 'image-app', triggers, inputFields },
  global: { plugins: [i18n] },
})

describe('WorkflowApiPanel', () => {
  it('shows only the web entry for a form trigger', () => {
    const wrapper = mountPanel(['form'])

    expect(wrapper.text()).toContain('GET https://example.com/apps/image-app')
    expect(wrapper.text()).not.toContain('/run')
    expect(wrapper.text()).not.toContain('cURL')
    expect(wrapper.text()).not.toContain('/files')
  })

  it('shows the API endpoint, curl example, and file endpoint when required', () => {
    const wrapper = mountPanel(['api'], [{ type: 'files' }])

    expect(wrapper.text()).toContain('POST https://example.com/v1/apps/image-app/run')
    expect(wrapper.text()).toContain("curl -X POST 'https://example.com/v1/apps/image-app/run'")
    expect(wrapper.text()).toContain('POST https://example.com/v1/apps/image-app/files')
  })

  it('shows the webhook endpoint in its curl example', () => {
    const wrapper = mountPanel(['webhook'])

    expect(wrapper.text()).toContain('POST https://example.com/v1/apps/image-app/webhook')
    expect(wrapper.text()).toContain("curl -X POST 'https://example.com/v1/apps/image-app/webhook'")
    expect(wrapper.text()).not.toContain('/run')
  })

  it('explains when the trigger has no public endpoint', () => {
    const wrapper = mountPanel(['schedule'])

    expect(wrapper.text()).toContain('当前触发方式不提供公共访问端点。')
    expect(wrapper.text()).not.toContain('cURL')
  })
})
