export function safeLocalRedirect(value: unknown): string | null {
  if (typeof value !== 'string' || !value.startsWith('/') || value.startsWith('//')) return null
  if (value.includes('\\')) return null
  return value
}
