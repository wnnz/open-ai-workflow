// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { consumeRunEvents } from '@/api/runEvents'
import PublicAppPage from './PublicAppPage.vue'

const { auth, replace } = vi.hoisted(() => ({
  auth: {
    token: null as string | null,
    user: null as any,
    authenticated: false,
    refresh: vi.fn(),
    logout: vi.fn(),
  },
  replace: vi.fn(),
}))

vi.mock('axios', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { slug: 'image-app' }, fullPath: '/apps/image-app' }),
  useRouter: () => ({ replace }),
}))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key: string, params?: any) => params?.name ? `${key}:${params.name}` : key }) }))
vi.mock('@/api/runEvents', () => ({ consumeRunEvents: vi.fn() }))
vi.mock('@/stores/auth', () => ({ useAuthStore: () => auth }))

const application = {
  name: 'Image app',
  access: 'public',
  triggers: ['form'],
  input_fields: [{ name: 'prompt', type: 'text', required: true, default_value: 'Autumn river' }],
}

function mountPage() {
  return mount(PublicAppPage, {
    global: {
      mocks: { $t: (key: string) => key },
      stubs: {
        InputText: {
          props: ['modelValue'],
          emits: ['update:modelValue'],
          template: '<input :type="$attrs.type" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" />',
        },
        WorkflowInputField: { template: '<input />' },
        WorkflowOutputRenderer: { props: ['output'], template: '<div data-testid="output">{{ JSON.stringify(output) }}</div>' },
      },
    },
  })
}

describe('PublicAppPage', () => {
  beforeEach(() => {
    vi.mocked(axios.get).mockReset()
    vi.mocked(axios.post).mockReset()
    vi.mocked(consumeRunEvents).mockReset()
    auth.token = null
    auth.user = null
    auth.authenticated = false
    auth.refresh.mockReset()
    auth.logout.mockReset()
    replace.mockReset()
    sessionStorage.clear()
  })

  it('prevents duplicate submissions and reads the created run by its fixed id', async () => {
    let finishStream!: () => void
    const streamFinished = new Promise<void>(resolve => { finishStream = resolve })
    vi.mocked(axios.get)
      .mockResolvedValueOnce({ data: application })
      .mockResolvedValueOnce({ data: { run_id: 'run-1', status: 'succeeded', outputs: { images: ['image-1'] } } })
    vi.mocked(axios.post).mockResolvedValue({ data: { run_id: 'run-1', status: 'pending', outputs: {} } })
    vi.mocked(consumeRunEvents).mockImplementation(async () => streamFinished)

    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('form').trigger('submit')
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(axios.post).toHaveBeenCalledTimes(1)
    expect(wrapper.text()).toContain('publicApp.running')
    expect(wrapper.find('[data-testid="output"]').exists()).toBe(false)

    finishStream()
    await flushPromises()

    expect(axios.get).toHaveBeenLastCalledWith('/v1/apps/image-app/runs/run-1', { headers: {} })
    expect(wrapper.get('[data-testid="output"]').text()).toContain('image-1')
  })

  it('restores the last public run after a refresh', async () => {
    sessionStorage.setItem('weaverun:public-run:image-app', 'run-restored')
    vi.mocked(axios.get)
      .mockResolvedValueOnce({ data: application })
      .mockResolvedValueOnce({ data: { run_id: 'run-restored', status: 'succeeded', outputs: { images: ['restored-image'] } } })

    const wrapper = mountPage()
    await flushPromises()

    expect(axios.get).toHaveBeenLastCalledWith('/v1/apps/image-app/runs/run-restored', { headers: {} })
    expect(wrapper.get('[data-testid="output"]').text()).toContain('restored-image')
  })

  it('redirects protected forms to login without showing an API key field', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({ data: { ...application, access: 'protected', access_options: { login: true, password: false } } })

    const wrapper = mountPage()
    await flushPromises()

    expect(replace).toHaveBeenCalledWith({ path: '/login', query: { redirect: '/apps/image-app' } })
    expect(wrapper.text()).not.toContain('API Key')
  })

  it('uses the signed-in user for a protected form run', async () => {
    auth.token = 'session-token'
    auth.user = { id: 'user-1', display_name: 'Alice' }
    auth.authenticated = true
    auth.refresh.mockResolvedValue(auth.user)
    vi.mocked(axios.get)
      .mockResolvedValueOnce({ data: { ...application, access: 'protected', access_options: { login: true, password: false } } })
      .mockResolvedValueOnce({ data: { run_id: 'run-protected', status: 'succeeded', outputs: {} } })
    vi.mocked(axios.post)
      .mockResolvedValueOnce({ data: { authorized: true, user_id: 'user-1' } })
      .mockResolvedValueOnce({ data: { run_id: 'run-protected', status: 'pending', outputs: {} } })
    vi.mocked(consumeRunEvents).mockResolvedValue(undefined)

    const wrapper = mountPage()
    await flushPromises()
    await wrapper.get('form').trigger('submit')
    await flushPromises()

    expect(wrapper.text()).toContain('Alice')
    expect(wrapper.text()).not.toContain('API Key')
    expect(axios.post).toHaveBeenCalledWith('/v1/apps/image-app/form', expect.anything(), {
      headers: { Authorization: 'Bearer session-token', 'Content-Type': 'application/json' },
    })
    expect(consumeRunEvents).toHaveBeenCalledWith(expect.any(String), expect.any(Function), {
      Authorization: 'Bearer session-token',
    })
  })

  it('unlocks a protected form with a password grant instead of an API key', async () => {
    vi.mocked(axios.get).mockResolvedValueOnce({
      data: { ...application, access: 'protected', access_options: { login: false, password: true } },
    })
    vi.mocked(axios.post).mockResolvedValueOnce({ data: { authorized: true, access_token: 'app-grant-token' } })

    const wrapper = mountPage()
    await flushPromises()
    expect(replace).not.toHaveBeenCalled()
    expect(wrapper.text()).not.toContain('API Key')

    await wrapper.get('input[type="password"]').setValue('partner-password')
    await wrapper.get('section form').trigger('submit')
    await flushPromises()

    expect(axios.post).toHaveBeenCalledWith('/v1/apps/image-app/access', { password: 'partner-password' })
    expect(sessionStorage.getItem('weaverun:app-access:image-app')).toBe('app-grant-token')
    expect(wrapper.find('form.surface').exists()).toBe(true)
  })
})
