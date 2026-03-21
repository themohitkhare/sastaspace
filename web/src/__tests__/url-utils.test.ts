import { describe, it, expect } from 'vitest'
import { validateUrl, extractDomain } from '@/lib/url-utils'

describe('validateUrl', () => {
  it('returns invalid for empty string', () => {
    const result = validateUrl('')
    expect(result.valid).toBe(false)
    expect(result.error).toBe('Please enter a valid website address')
  })

  it('returns invalid for whitespace-only input', () => {
    const result = validateUrl('   ')
    expect(result.valid).toBe(false)
  })

  it('accepts a valid URL with https', () => {
    const result = validateUrl('https://example.com')
    expect(result.valid).toBe(true)
    expect(result.url).toBe('https://example.com/')
  })

  it('accepts a valid URL with http', () => {
    const result = validateUrl('http://example.com')
    expect(result.valid).toBe(true)
    expect(result.url).toBe('http://example.com/')
  })

  it('prepends https:// when no protocol is provided', () => {
    const result = validateUrl('example.com')
    expect(result.valid).toBe(true)
    expect(result.url).toBe('https://example.com/')
  })

  it('returns invalid for hostname without a dot', () => {
    const result = validateUrl('localhost')
    expect(result.valid).toBe(false)
    expect(result.error).toBe('Please enter a valid website address')
  })

  it('returns invalid for completely malformed input', () => {
    const result = validateUrl('not a url at all !!!')
    expect(result.valid).toBe(false)
  })

  it('handles URLs with paths', () => {
    const result = validateUrl('https://example.com/path/page')
    expect(result.valid).toBe(true)
    expect(result.url).toContain('/path/page')
  })

  it('handles subdomains', () => {
    const result = validateUrl('sub.example.com')
    expect(result.valid).toBe(true)
    expect(result.url).toBe('https://sub.example.com/')
  })

  it('trims whitespace from input', () => {
    const result = validateUrl('  example.com  ')
    expect(result.valid).toBe(true)
    expect(result.url).toBe('https://example.com/')
  })
})

describe('extractDomain', () => {
  it('extracts domain from a full URL', () => {
    expect(extractDomain('https://example.com/path')).toBe('example.com')
  })

  it('strips www. prefix', () => {
    expect(extractDomain('https://www.example.com')).toBe('example.com')
  })

  it('handles input without protocol', () => {
    expect(extractDomain('example.com')).toBe('example.com')
  })

  it('handles input with www. and no protocol', () => {
    expect(extractDomain('www.example.com')).toBe('example.com')
  })

  it('preserves subdomains other than www', () => {
    expect(extractDomain('https://blog.example.com')).toBe('blog.example.com')
  })

  it('returns raw input on parse failure', () => {
    expect(extractDomain('')).toBe('')
  })
})
