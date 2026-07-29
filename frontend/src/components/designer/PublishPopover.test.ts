// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import PrimeVue from 'primevue/config'
import { i18n } from '@/i18n'
import PublishPopover from './PublishPopover.vue'

describe('PublishPopover', () => {
  it('publishes with selected access and change note', async () => {
    const wrapper = mount(PublishPopover, {
      props: { open: true, workflow: { published_access: 'public' }, versions: [] },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })
    await wrapper.find('select').setValue('protected')
    await wrapper.find('input').setValue('Release for the team')
    const publishButton = wrapper.findAll('button').find(button => button.text().includes('发布'))
    expect(publishButton).toBeTruthy()
    await publishButton!.trigger('click')
    expect(wrapper.emitted('publish')?.[0]).toEqual([{
      access: 'protected',
      change_note: 'Release for the team',
      all_users_enabled: true,
      all_users_expires_at: null,
      user_grants: [],
      password_grants: [],
    }])
  })

  it('shows latest version and published shortcuts without a separate access badge', async () => {
    const wrapper = mount(PublishPopover, {
      props: {
        open: true,
        workflow: { published_version_id: 'version-2', published_access: 'protected' },
        versions: [{ id: 'version-2', version: 2, created_at: '2026-07-24T12:00:00Z' }],
      },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })
    expect(wrapper.text()).toContain('v2')
    expect(wrapper.text()).toContain('打开已发布应用')
    expect(wrapper.findAll('.publish-shortcut')).toHaveLength(3)
    expect(wrapper.find('.publish-shortcut.cursor-default').exists()).toBe(false)
    const apiButton = wrapper.findAll('button').find(button => button.text().includes('发布与接入'))
    await apiButton!.trigger('click')
    expect(wrapper.emitted('api')).toHaveLength(1)
  })

  it('organizes protected grants as a compact three-row list', async () => {
    const wrapper = mount(PublishPopover, {
      props: { open: true, workflow: { published_access: 'public' }, versions: [] },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })
    await wrapper.find('select').setValue('protected')
    expect(wrapper.findAll('.access-row')).toHaveLength(3)
    expect(wrapper.text()).toContain('所有登录用户')
    expect(wrapper.text()).toContain('指定用户')
    expect(wrapper.text()).toContain('访问密码')
  })

  it('allows a non-empty password without a length rule', async () => {
    const wrapper = mount(PublishPopover, {
      props: { open: true, workflow: { published_access: 'public' }, versions: [] },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })
    await wrapper.find('select').setValue('protected')
    await wrapper.findAll('details')[1].find('button').trigger('click')
    const passwordInput = wrapper.find('input[type="password"]')
    await passwordInput.setValue('123456')
    const publishButton = wrapper.findAll('button').find(button => button.text().includes('发布'))
    expect(publishButton?.attributes('disabled')).toBeUndefined()
  })
})
