import { describe, it, expect, vi, beforeEach } from 'vitest'
import { streamRedesign } from '@/lib/sse-client'

// Helper to create a ReadableStream from SSE text chunks
function createSSEStream(chunks: string[]): ReadableStream<Uint8Array> {
  const encoder = new TextEncoder()
  let index = 0
  return new ReadableStream({
    pull(controller) {
      if (index < chunks.length) {
        controller.enqueue(encoder.encode(chunks[index]))
        index++
      } else {
        controller.close()
      }
    },
  })
}

beforeEach(() => {
  vi.restoreAllMocks()
})

describe('streamRedesign', () => {
  it('yields parsed SSE events', async () => {
    const sseChunks = [
      'event: crawling\ndata: {"status":"started"}\n\n',
      'event: done\ndata: {"subdomain":"test-com"}\n\n',
    ]

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream(sseChunks),
    } as unknown as Response)

    const events = []
    for await (const event of streamRedesign('https://test.com', 'http://localhost:8080')) {
      events.push(event)
    }

    expect(events).toHaveLength(2)
    expect(events[0]).toEqual({ event: 'crawling', data: { status: 'started' } })
    expect(events[1]).toEqual({ event: 'done', data: { subdomain: 'test-com' } })
  })

  it('uses default event name "message" when no event line is present', async () => {
    const sseChunks = ['data: {"hello":"world"}\n\n']

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream(sseChunks),
    } as unknown as Response)

    const events = []
    for await (const event of streamRedesign('https://test.com')) {
      events.push(event)
    }

    expect(events).toHaveLength(1)
    expect(events[0].event).toBe('message')
  })

  it('skips events with empty data', async () => {
    const sseChunks = ['event: crawling\n\n']

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream(sseChunks),
    } as unknown as Response)

    const events = []
    for await (const event of streamRedesign('https://test.com')) {
      events.push(event)
    }

    expect(events).toHaveLength(0)
  })

  it('skips malformed JSON data silently', async () => {
    const sseChunks = [
      'event: crawling\ndata: not-json\n\n',
      'event: done\ndata: {"subdomain":"ok"}\n\n',
    ]

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream(sseChunks),
    } as unknown as Response)

    const events = []
    for await (const event of streamRedesign('https://test.com')) {
      events.push(event)
    }

    expect(events).toHaveLength(1)
    expect(events[0].event).toBe('done')
  })

  it('throws on non-ok HTTP response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
      json: async () => ({ error: 'Server error' }),
    } as unknown as Response)

    await expect(async () => {
      for await (const _ of streamRedesign('https://test.com')) {
        // consume
      }
    }).rejects.toThrow('Server error')
  })

  it('throws generic HTTP error when response body has no error field', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 502,
      json: async () => ({}),
    } as unknown as Response)

    await expect(async () => {
      for await (const _ of streamRedesign('https://test.com')) {
        // consume
      }
    }).rejects.toThrow('HTTP 502')
  })

  it('handles chunked SSE data split across reads', async () => {
    // Split a single event across two chunks
    const sseChunks = [
      'event: crawling\ndata: {"sta',
      'tus":"started"}\n\n',
    ]

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream(sseChunks),
    } as unknown as Response)

    const events = []
    for await (const event of streamRedesign('https://test.com')) {
      events.push(event)
    }

    expect(events).toHaveLength(1)
    expect(events[0]).toEqual({ event: 'crawling', data: { status: 'started' } })
  })

  it('sends POST request with correct URL and body', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream([]),
    } as unknown as Response)

    for await (const _ of streamRedesign('https://example.com', 'http://api.test')) {
      // consume
    }

    expect(fetchSpy).toHaveBeenCalledWith(
      'http://api.test/redesign',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://example.com' }),
      })
    )
  })
})
