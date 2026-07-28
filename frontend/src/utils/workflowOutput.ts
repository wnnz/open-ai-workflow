const DATA_IMAGE = /^data:image\/[a-z0-9.+-]+;base64,/i
const REMOTE_IMAGE = /^https?:\/\//i

export function collectWorkflowImages(value: unknown): string[] {
  const images: string[] = []
  const seen = new Set<string>()

  function visit(item: unknown, imageContext = false) {
    if (typeof item === 'string') {
      if ((DATA_IMAGE.test(item) || (imageContext && REMOTE_IMAGE.test(item))) && !seen.has(item)) {
        seen.add(item)
        images.push(item)
      }
      return
    }
    if (Array.isArray(item)) {
      item.forEach(entry => visit(entry, imageContext))
      return
    }
    if (!item || typeof item !== 'object') return
    Object.entries(item as Record<string, unknown>).forEach(([key, entry]) => {
      visit(entry, imageContext || /image|picture|photo/i.test(key))
    })
  }

  visit(value)
  return images
}

export function compactWorkflowOutput(value: unknown): unknown {
  if (typeof value === 'string') {
    if (DATA_IMAGE.test(value)) {
      const mediaType = value.slice(5, value.indexOf(';'))
      return `[${mediaType} image data, ${(value.length / 1024).toFixed(1)} KB]`
    }
    return value
  }
  if (Array.isArray(value)) return value.map(compactWorkflowOutput)
  if (!value || typeof value !== 'object') return value
  return Object.fromEntries(Object.entries(value as Record<string, unknown>).map(([key, item]) => [key, compactWorkflowOutput(item)]))
}
