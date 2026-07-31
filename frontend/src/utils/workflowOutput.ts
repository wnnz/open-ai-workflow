const DATA_IMAGE = /^data:image\/[a-z0-9.+-]+;base64,/i
const REMOTE_IMAGE = /^https?:\/\//i

export type WorkflowFileOutput = {
  id: string
  filename: string
  content_type: string
  size: number
  download_url: string
}

export function collectWorkflowFiles(value: unknown): WorkflowFileOutput[] {
  const files: WorkflowFileOutput[] = []
  const seen = new Set<string>()

  function visit(item: unknown) {
    if (Array.isArray(item)) return item.forEach(visit)
    if (!item || typeof item !== 'object') return
    const record = item as Record<string, unknown>
    if (record.id && record.filename && record.download_url) {
      const id = String(record.id)
      if (!seen.has(id)) {
        seen.add(id)
        files.push({
          id,
          filename: String(record.filename),
          content_type: String(record.content_type || 'application/octet-stream'),
          size: Number(record.size || 0),
          download_url: String(record.download_url),
        })
      }
      return
    }
    Object.values(record).forEach(visit)
  }

  visit(value)
  return files
}

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
