import { describe, it, expect, vi, beforeEach } from 'vitest'
import { submitRedesign, streamJobStatus } from '@/lib/sse-client'

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

describe('submitRedesign', () => {
  it('returns job_id on success', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'test-job-123' }),
    } as unknown as Response)

    const jobId = await submitRedesign('https://example.com')
    expect(jobId).toBe('test-job-123')
  })

  it('throws on non-ok response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 500,
    } as unknown as Response)

    await expect(submitRedesign('https://example.com')).rejects.toThrow(
      'Redesign request failed: 500'
    )
  })

  it('throws when no job_id in response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({}),
    } as unknown as Response)

    await expect(submitRedesign('https://example.com')).rejects.toThrow(
      'No job_id returned from server'
    )
  })

  it('sends POST to correct URL with body', async () => {
    const fetchSpy = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => ({ job_id: 'abc' }),
    } as unknown as Response)

    await submitRedesign('https://example.com', 'premium')

    expect(fetchSpy).toHaveBeenCalledWith(
      'http://localhost:8080/redesign',
      expect.objectContaining({
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: 'https://example.com', tier: 'premium' }),
      })
    )
  })
})

describe('streamJobStatus', () => {
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
    for await (const event of streamJobStatus('test-job-123')) {
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
    for await (const event of streamJobStatus('job-1')) {
      events.push(event)
    }

    expect(events).toHaveLength(1)
    expect(events[0].event).toBe('message')
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
    for await (const event of streamJobStatus('job-1')) {
      events.push(event)
    }

    expect(events).toHaveLength(1)
    expect(events[0].event).toBe('done')
  })

  it('throws on non-ok HTTP response', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: false,
      status: 404,
      body: null,
    } as unknown as Response)

    await expect(async () => {
      // eslint-disable-next-line @typescript-eslint/no-unused-vars
      for await (const _ of streamJobStatus('nonexistent')) {
        // consume
      }
    }).rejects.toThrow('Stream failed: 404')
  })

  it('handles chunked SSE data split across reads', async () => {
    const sseChunks = [
      'event: crawling\ndata: {"sta',
      'tus":"started"}\n\n',
    ]

    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      body: createSSEStream(sseChunks),
    } as unknown as Response)

    const events = []
    for await (const event of streamJobStatus('job-1')) {
      events.push(event)
    }

    expect(events).toHaveLength(1)
    expect(events[0]).toEqual({ event: 'crawling', data: { status: 'started' } })
  })
})
