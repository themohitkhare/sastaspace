/**
 * Tests for useSastaPolling hook
 */
import { renderHook } from '@testing-library/react'
import { vi, beforeEach, afterEach } from 'vitest'
import { useSastaPolling } from '../../src/hooks/useSastaPolling'
import { useGameStore } from '../../src/store/useGameStore'
import { apiClient } from '../../src/api/apiClient'

vi.mock('../../src/store/useGameStore')
vi.mock('../../src/api/apiClient')

describe('useSastaPolling', () => {
  let mockSetGame
  let mockSetError
  let mockVersion

  beforeEach(() => {
    vi.clearAllMocks()
    vi.useRealTimers() // Use real timers for simplicity
    
    mockVersion = 0
    mockSetGame = vi.fn()
    mockSetError = vi.fn()

    useGameStore.mockImplementation((selector) => {
      const state = {
        version: mockVersion,
        setGame: mockSetGame,
        setError: mockSetError,
      }
      return selector(state)
    })

    apiClient.get = vi.fn().mockResolvedValue({
      status: 200,
      data: {
        version: 1,
        game: { id: 'game-123', status: 'ACTIVE' },
      },
    })
  })

  afterEach(() => {
    vi.clearAllTimers()
  })

  it('polls game state on mount', async () => {
    renderHook(() => useSastaPolling('game-123', 100))

    // Wait for initial poll
    await new Promise(resolve => setTimeout(resolve, 150))

    expect(apiClient.get).toHaveBeenCalledWith(
      '/sastadice/games/game-123/state',
      expect.objectContaining({
        params: { version: 0 },
        validateStatus: expect.any(Function),
      })
    )
  })

  it('updates game state when receiving 200 response', async () => {
    renderHook(() => useSastaPolling('game-123', 100))

    await new Promise(resolve => setTimeout(resolve, 150))

    expect(mockSetGame).toHaveBeenCalledWith(
      { id: 'game-123', status: 'ACTIVE' },
      1
    )
  })

  it('skips update when receiving 304 response', async () => {
    apiClient.get = vi.fn().mockResolvedValue({
      status: 304,
    })

    renderHook(() => useSastaPolling('game-123', 100))

    await new Promise(resolve => setTimeout(resolve, 150))

    expect(apiClient.get).toHaveBeenCalled()
    expect(mockSetGame).not.toHaveBeenCalled()
  })

  it('handles 304 errors gracefully', async () => {
    apiClient.get = vi.fn().mockRejectedValue({
      response: { status: 304 },
    })

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    renderHook(() => useSastaPolling('game-123', 100))

    await new Promise(resolve => setTimeout(resolve, 150))

    expect(apiClient.get).toHaveBeenCalled()
    expect(mockSetError).not.toHaveBeenCalled()
    consoleError.mockRestore()
  })

  it('handles errors and sets error state', async () => {
    apiClient.get = vi.fn().mockRejectedValue({
      response: { status: 500 },
      message: 'Server error',
    })

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    renderHook(() => useSastaPolling('game-123', 100))

    await new Promise(resolve => setTimeout(resolve, 150))
    
    expect(mockSetError).toHaveBeenCalledWith('Server error')
    consoleError.mockRestore()
  })

  it('does not poll when gameId is null', async () => {
    renderHook(() => useSastaPolling(null, 100))

    await new Promise(resolve => setTimeout(resolve, 150))

    expect(apiClient.get).not.toHaveBeenCalled()
  })

  it('polls at specified interval', async () => {
    renderHook(() => useSastaPolling('game-123', 100))

    // Wait for initial poll (immediate) + first interval poll
    await new Promise(resolve => setTimeout(resolve, 50))
    const initialCalls = apiClient.get.mock.calls.length
    expect(initialCalls).toBeGreaterThanOrEqual(1)

    // Wait for next interval
    await new Promise(resolve => setTimeout(resolve, 100))
    expect(apiClient.get).toHaveBeenCalledTimes(initialCalls + 1)
  })

  it('cleans up interval on unmount', async () => {
    const { unmount } = renderHook(() => useSastaPolling('game-123', 100))

    // Wait for initial poll
    await new Promise(resolve => setTimeout(resolve, 50))
    const callsBeforeUnmount = apiClient.get.mock.calls.length
    expect(callsBeforeUnmount).toBeGreaterThanOrEqual(1)

    unmount()

    // Wait to see if polling continues
    await new Promise(resolve => setTimeout(resolve, 100))

    // Should not poll after unmount (calls should remain the same)
    expect(apiClient.get).toHaveBeenCalledTimes(callsBeforeUnmount)
  })
})
