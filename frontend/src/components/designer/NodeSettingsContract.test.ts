import { describe, expect, it } from 'vitest'

const panelSources = import.meta.glob('./*ConfigPanel.vue', {
  eager: true,
  import: 'default',
  query: '?raw',
}) as Record<string, string>

const pageSources = import.meta.glob('../../pages/WorkflowDesignerPage.vue', {
  eager: true,
  import: 'default',
  query: '?raw',
}) as Record<string, string>

describe('node settings visual contract', () => {
  it('gives every standalone config panel the shared parameters section', () => {
    const panels = Object.entries(panelSources)
    expect(panels.length).toBeGreaterThan(10)

    for (const [panel, source] of panels) {
      expect(source, panel).toContain('kind="parameters"')
      expect(source, panel).toContain("designer.nodeParameters")
    }
  })

  it('uses the same sections for inline start, end, note, JSON, and delay nodes', () => {
    const source = Object.values(pageSources)[0] || ''
    for (const type of ['note', 'start', 'end', 'json', 'delay']) expect(source).toContain(`selectedType === '${type}'`)
    expect(source.match(/kind="parameters"/g)?.length || 0).toBeGreaterThanOrEqual(4)
    expect(source).toContain('kind="input"')
    expect(source).toContain('kind="output"')
  })
})
