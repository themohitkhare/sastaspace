/**
 * Tests for apiClient
 * Note: apiClient is primarily configuration code, testing is limited to basic structure
 */
import { describe, it, expect } from 'vitest'
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
})
