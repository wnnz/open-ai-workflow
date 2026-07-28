export type RunEvent = Record<string, any> & { type?: string }

export async function consumeRunEvents(
  url: string,
  onEvent: (event: RunEvent) => void,
  extraHeaders: Record<string, string> = {},
) {
  const token = localStorage.getItem('access_token')
  const response = await fetch(url, {
    headers: { Accept: 'text/event-stream', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...extraHeaders },
  })
  if (!response.ok || !response.body) throw new Error(`Run event stream failed with HTTP ${response.status}`)
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  while (true) {
    const { done, value } = await reader.read()
    buffer += decoder.decode(value || new Uint8Array(), { stream: !done })
    const blocks = buffer.split('\n\n')
    buffer = blocks.pop() || ''
    for (const block of blocks) {
      const data = block.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trim()).join('\n')
      if (data) onEvent(JSON.parse(data))
    }
    if (done) break
  }
}
