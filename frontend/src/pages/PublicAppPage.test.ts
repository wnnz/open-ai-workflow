// @vitest-environment jsdom

import { flushPromises, mount } from '@vue/test-utils'
import axios from 'axios'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { consumeRunEvents } from '@/api/runEvents'
import PublicAppPage from './PublicAppPage.vue'

vi.mock('axios', () => ({ default: { get: vi.fn(), post: vi.fn() } }))
vi.mock('vue-router', () => ({ useRoute: () => ({ params: { slug: 'image-app' } }) }))
vi.mock('vue-i18n', () => ({ useI18n: () => ({ t: (key: string) => key }) }))
vi.mock('@/api/runEvents', () => ({ consumeRunEvents: vi.fn() }))

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
})
