// @vitest-environment jsdom

import { mount } from '@vue/test-utils'
import { describe, expect, it } from 'vitest'
import { i18n } from '@/i18n'
import WorkflowDesignerSidebar from './WorkflowDesignerSidebar.vue'

describe('WorkflowDesignerSidebar', () => {
  it('renders application navigation and emits shell actions', async () => {
    const wrapper = mount(WorkflowDesignerSidebar, {
      props: {
        workflowName: '文档助手',
        userName: 'Codex Demo',
        activeSection: 'orchestration',
        dark: false,
      },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).toContain('文档助手')
    expect(wrapper.text()).toContain('访问 API')
    expect(wrapper.get('button[aria-current="page"]').text()).toContain('编排')
    await wrapper.findAll('nav button').find(button => button.text().includes('访问 API'))!.trigger('click')
    await wrapper.get('button[title="收起侧边栏"]').trigger('click')
    await wrapper.get('button[title="设计器帮助"]').trigger('click')

    expect(wrapper.emitted('selectSection')).toEqual([['api']])
    expect(wrapper.emitted('toggleCollapsed')).toHaveLength(1)
    expect(wrapper.emitted('help')).toHaveLength(1)
  })

  it('keeps navigation accessible when collapsed', () => {
    const wrapper = mount(WorkflowDesignerSidebar, {
      props: { collapsed: true, workflowName: '文档助手', userName: 'Codex Demo', activeSection: 'logs' },
      global: { plugins: [i18n] },
    })

    expect(wrapper.text()).not.toContain('文档助手')
    expect(wrapper.get('button[title="日志"]').attributes('aria-current')).toBe('page')
    expect(wrapper.get('button[title="展开侧边栏"]').attributes('aria-label')).toBe('展开侧边栏')
  })
})
