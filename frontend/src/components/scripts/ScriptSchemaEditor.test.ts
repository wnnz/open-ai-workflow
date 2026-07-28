// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import PrimeVue from 'primevue/config'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import ScriptSchemaEditor from './ScriptSchemaEditor.vue'

describe('ScriptSchemaEditor', () => {
  it('creates typed parameters from the visual editor', async () => {
    const wrapper = mount(ScriptSchemaEditor, {
      props: { modelValue: { type: 'object', properties: {} } },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })

    await wrapper.get('button[aria-label="添加参数"]').trigger('click')

    expect(wrapper.emitted('update:modelValue')?.[0]?.[0]).toEqual({
      type: 'object',
      properties: { input1: { type: 'string', description: '' } },
      required: [],
    })
  })

  it('offers an advanced JSON Schema editor', async () => {
    const wrapper = mount(ScriptSchemaEditor, {
      props: { modelValue: { type: 'object', properties: {} } },
      global: { plugins: [i18n, [PrimeVue, { unstyled: true }]] },
    })

    await wrapper.get('button.text-xs').trigger('click')

    expect(wrapper.find('textarea').exists()).toBe(true)
  })
})
