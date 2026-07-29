// @vitest-environment jsdom

import { afterEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import ToastContainer from './ToastContainer.vue'
import { clearToasts, showToast, toastMessages } from '@/composables/useToast'
import { i18n } from '@/i18n'

describe('ToastContainer', () => {
  afterEach(() => {
    clearToasts()
    vi.useRealTimers()
    document.body.innerHTML = ''
  })

  it('renders notifications in the global top overlay and dismisses them', async () => {
    const wrapper = mount(ToastContainer, { attachTo: document.body, global: { plugins: [i18n] } })
    showToast('发布成功，最新版本已生效。', 'success', 0)
    await wrapper.vm.$nextTick()

    const notice = document.body.querySelector('[role="status"]')
    expect(notice?.textContent).toContain('发布成功，最新版本已生效。')
    expect(notice?.closest('.fixed')?.className).toContain('top-4')

    ;(notice?.querySelector('button') as HTMLButtonElement).click()
    await wrapper.vm.$nextTick()
    expect(toastMessages.value).toHaveLength(0)
    wrapper.unmount()
  })

  it('deduplicates matching messages and automatically dismisses them', () => {
    vi.useFakeTimers()
    const first = showToast('请求失败', 'error', 1000)
    const second = showToast('请求失败', 'error', 1000)

    expect(second).toBe(first)
    expect(toastMessages.value).toHaveLength(1)
    vi.advanceTimersByTime(1000)
    expect(toastMessages.value).toHaveLength(0)
  })
})
