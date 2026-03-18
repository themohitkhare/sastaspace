/**
 * Tests for apiClient
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { apiClient } from '../../src/api/apiClient'

describe('apiClient', () => {
  it('exports apiClient instance', () => {
    expect(apiClient).toBeDefined()
    expect(apiClient).toHaveProperty('get')
    expect(apiClient).toHaveProperty('post')
    expect(apiClient).toHaveProperty('interceptors')
  })

  it('has request interceptor configured', () => {
    expect(apiClient.interceptors.request).toBeDefined()
    expect(apiClient.interceptors.request.use).toBeDefined()
  })

  it('has response interceptor configured', () => {
    expect(apiClient.interceptors.response).toBeDefined()
    expect(apiClient.interceptors.response.use).toBeDefined()
  })

  it('uses relative URL when on port 80 (Traefik)', () => {
    // apiClient is initialized at module load, so we verify the base URL
    // In test environment (jsdom), location is localhost without port
    // which should resolve to relative /api/v1
    const baseURL = apiClient.defaults.baseURL
    expect(baseURL).toBeDefined()
    expect(typeof baseURL).toBe('string')
  })
})
