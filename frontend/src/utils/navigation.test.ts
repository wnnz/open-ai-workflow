import { describe, expect, it } from 'vitest'
import { safeLocalRedirect } from './navigation'

describe('safeLocalRedirect', () => {
  it('accepts local application paths', () => {
    expect(safeLocalRedirect('/apps/image-app?source=login')).toBe('/apps/image-app?source=login')
  })

  it('rejects external and malformed redirect targets', () => {
    expect(safeLocalRedirect('https://example.com')).toBeNull()
    expect(safeLocalRedirect('//example.com/path')).toBeNull()
    expect(safeLocalRedirect('/\\example.com/path')).toBeNull()
  })
})
