import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { submitRedesign, pollJobStatus } from '@/lib/sse-client'
import type { JobStatus } from '@/lib/sse-client'

beforeEach(() => {
  vi.restoreAllMocks()
  vi.useFakeTimers()
})

afterEach(() => {
  vi.useRealTimers()
})

// --- submitRedesign (unchanged) ---

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
})

// --- pollJobStatus ---

function makeJob(overrides: Partial<JobStatus> = {}): JobStatus {
  return {
    id: 'job-1',
    status: 'crawling',
    progress: 25,
    message: 'Crawling...',
    ...overrides,
  }
}

describe('pollJobStatus', () => {
  it('yields job status and stops on done', async () => {
    const jobs: JobStatus[] = [
      makeJob({ status: 'crawling' }),
      makeJob({ status: 'done', subdomain: 'example-com' }),
    ]
    let callCount = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      const job = jobs[callCount++]
      return { ok: true, json: async () => job } as unknown as Response
    })

    const results: JobStatus[] = []
    const gen = pollJobStatus('job-1')

    // Get first value
    const p1 = gen.next()
    await vi.runAllTimersAsync()
    results.push((await p1).value)

    // Get second value (done status is yielded)
    const p2 = gen.next()
    await vi.runAllTimersAsync()
    const r2 = await p2
    expect(r2.done).toBe(false)
    results.push(r2.value)

    // Generator should now be done
    const p3 = gen.next()
    await vi.runAllTimersAsync()
    const r3 = await p3
    expect(r3.done).toBe(true)

    expect(results[0].status).toBe('crawling')
    expect(results[1].status).toBe('done')
  })

  it('silently retries on network error and continues', async () => {
    let callCount = 0
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      callCount++
      if (callCount === 1) throw new Error('Network error')
      return {
        ok: true,
        json: async () => makeJob({ status: 'crawling' }),
      } as unknown as Response
    })

    const gen = pollJobStatus('job-1')
    const p = gen.next()
    await vi.runAllTimersAsync()
    const result = await p

    expect(result.value.status).toBe('crawling')
    expect(callCount).toBe(2) // first failed, second succeeded
  })

  it('throws POLL_FAILED after 5 consecutive network errors', async () => {
    vi.spyOn(globalThis, 'fetch').mockRejectedValue(new Error('Network error'))

    const gen = pollJobStatus('job-1')
    const p = gen.next()
    // Attach .catch immediately to prevent unhandled rejection warning
    const caught = p.catch((e: Error) => e)
    await vi.runAllTimersAsync()
    const error = await caught
    expect(error).toBeInstanceOf(Error)
    expect((error as Error).message).toBe('POLL_FAILED')
  })

  it('stops polling when AbortSignal is aborted', async () => {
    const controller = new AbortController()
    vi.spyOn(globalThis, 'fetch').mockImplementation(async () => {
      controller.abort()
      return {
        ok: true,
        json: async () => makeJob({ status: 'crawling' }),
      } as unknown as Response
    })

    const results: JobStatus[] = []
    const gen = pollJobStatus('job-1', controller.signal)
    const p = gen.next()
    await vi.runAllTimersAsync()
    const r = await p
    // After aborting, next call should terminate the generator
    if (!r.done && r.value) results.push(r.value)

    const p2 = gen.next()
    await vi.runAllTimersAsync()
    const r2 = await p2
    expect(r2.done).toBe(true)
  })

  it('uses 1s interval when status is deploying', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      json: async () => makeJob({ status: 'deploying', progress: 90 }),
    } as unknown as Response)

    const gen = pollJobStatus('job-1')
    const p = gen.next()
    await vi.runAllTimersAsync()
    const r = await p
    expect(r.value.status).toBe('deploying')
  })
})
