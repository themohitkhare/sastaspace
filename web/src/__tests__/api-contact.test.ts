import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockSend = vi.fn().mockResolvedValue({ error: null })

// Mock Resend before importing the route
vi.mock('resend', () => ({
  Resend: function () {
    return {
      emails: {
        send: mockSend,
      },
    }
  },
}))

import { POST } from '@/app/api/contact/route'
import { NextRequest } from 'next/server'

function makeRequest(body: Record<string, unknown>): NextRequest {
  return new NextRequest('http://localhost:3000/api/contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
}

beforeEach(() => {
  mockSend.mockReset().mockResolvedValue({ error: null })
  vi.stubEnv('NEXT_PUBLIC_ENABLE_TURNSTILE', 'false')
  vi.stubEnv('RESEND_API_KEY', 'test-key')
  vi.stubEnv('OWNER_EMAIL', 'owner@test.com')
})

describe('POST /api/contact', () => {
  it('returns ok:true for honeypot-filled submissions (silent reject)', async () => {
    const req = makeRequest({
      name: 'Bot',
      email: 'bot@spam.com',
      message: 'Buy now!',
      website: 'http://spam.com', // honeypot filled
      subdomain: 'test-com',
    })

    const res = await POST(req)
    const data = await res.json()

    expect(data.ok).toBe(true)
    expect(res.status).toBe(200)
    // Honeypot short-circuits before sending email
    expect(mockSend).not.toHaveBeenCalled()
  })

  it('returns 400 when name is missing', async () => {
    const req = makeRequest({
      name: '',
      email: 'test@test.com',
      message: 'Hello',
      website: '',
      subdomain: 'test-com',
    })

    const res = await POST(req)
    const data = await res.json()

    expect(res.status).toBe(400)
    expect(data.error).toBe('All fields are required')
  })

  it('returns 400 when email is missing', async () => {
    const req = makeRequest({
      name: 'John',
      email: '',
      message: 'Hello',
      website: '',
      subdomain: 'test-com',
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })

  it('returns 400 when message is missing', async () => {
    const req = makeRequest({
      name: 'John',
      email: 'john@test.com',
      message: '   ',
      website: '',
      subdomain: 'test-com',
    })

    const res = await POST(req)
    expect(res.status).toBe(400)
  })

  it('sends email and returns ok:true on valid submission (Turnstile disabled)', async () => {
    const req = makeRequest({
      name: 'John',
      email: 'john@example.com',
      message: 'Hello there',
      website: '',
      subdomain: 'my-site-com',
    })

    const res = await POST(req)
    const data = await res.json()

    expect(res.status).toBe(200)
    expect(data.ok).toBe(true)
    expect(mockSend).toHaveBeenCalledOnce()
  })

  it('returns 500 when Resend returns an error', async () => {
    mockSend.mockResolvedValueOnce({ error: { message: 'Rate limited' } })

    const req = makeRequest({
      name: 'John',
      email: 'john@example.com',
      message: 'Hello',
      website: '',
      subdomain: 'test-com',
    })

    const res = await POST(req)
    const data = await res.json()

    expect(res.status).toBe(500)
    expect(data.error).toBe('Failed to send message')
  })

  it('escapes HTML in email content', async () => {
    const req = makeRequest({
      name: '<script>alert("xss")</script>',
      email: 'test@test.com',
      message: 'Hello <b>world</b>',
      website: '',
      subdomain: 'test-com',
    })

    const res = await POST(req)
    expect(res.status).toBe(200)

    const sendCall = mockSend.mock.calls[0]?.[0]
    expect(sendCall).toBeDefined()
    expect(sendCall.subject).toContain('&lt;script&gt;')
    expect(sendCall.html).not.toContain('<script>')
    expect(sendCall.html).toContain('&lt;b&gt;world&lt;/b&gt;')
  })
})
