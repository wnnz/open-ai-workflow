import { describe, expect, it } from 'vitest'

const pageSources = import.meta.glob('./ScriptsPage.vue', {
  eager: true,
  import: 'default',
  query: '?raw',
}) as Record<string, string>

const modalSources = import.meta.glob('../components/ui/ModalShell.vue', {
  eager: true,
  import: 'default',
  query: '?raw',
}) as Record<string, string>

describe('script editor layout contract', () => {
  it('lets the code editor shrink with the dialog and scroll internally', () => {
    const source = Object.values(pageSources)[0] || ''

    expect(source).toContain('panel-class="h-[92vh]"')
    expect(source).not.toContain('min-h-[660px]')
    expect(source).toContain('lg:h-full lg:min-h-0')
    expect(source).toContain('lg:flex lg:min-h-0 lg:flex-col')
    expect(source).toContain('lg:h-auto lg:min-h-0 lg:flex-1')
    expect(source).toContain('height="100%"')
  })

  it('supports sizing the dialog panel independently from its body', () => {
    const source = Object.values(modalSources)[0] || ''

    expect(source).toContain('panelClass?: string')
    expect(source).toContain(':class="[maxWidth, panelClass]"')
  })
})
