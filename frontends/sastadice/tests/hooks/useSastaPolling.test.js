/**
 * Tests for useSastaPolling hook
 */
import { renderHook, act, waitFor } from '@testing-library/react'
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
    vi.useFakeTimers()
    
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

    // Mock getState for the hook
    useGameStore.getState = vi.fn(() => ({
      version: mockVersion,
    }))

    apiClient.get = vi.fn().mockResolvedValue({
      status: 200,
      data: {
        version: 1,
        game: { id: 'game-123', status: 'ACTIVE' },
      },
    })
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllTimers()
  })

  it('returns refetch function', () => {
    const { result } = renderHook(() => useSastaPolling('game-123', 1000))
    
    expect(result.current).toHaveProperty('refetch')
    expect(typeof result.current.refetch).toBe('function')
  })

  it('polls game state on mount', async () => {
    renderHook(() => useSastaPolling('game-123', 1000))

    // Flush pending promises
    await vi.runOnlyPendingTimersAsync()

    expect(apiClient.get).toHaveBeenCalledWith(
      '/sastadice/games/game-123/state',
      expect.objectContaining({
        params: { version: 0 },
        validateStatus: expect.any(Function),
      })
    )
  })

  it('updates game state when receiving 200 response', async () => {
    renderHook(() => useSastaPolling('game-123', 1000))

    await vi.runOnlyPendingTimersAsync()

    expect(mockSetGame).toHaveBeenCalledWith(
      { id: 'game-123', status: 'ACTIVE' },
      1
    )
  })

  it('skips update when receiving 304 response', async () => {
    apiClient.get = vi.fn().mockResolvedValue({
      status: 304,
    })

    renderHook(() => useSastaPolling('game-123', 1000))

    await vi.runOnlyPendingTimersAsync()

    expect(apiClient.get).toHaveBeenCalled()
    expect(mockSetGame).not.toHaveBeenCalled()
  })

  it('handles 304 errors gracefully', async () => {
    apiClient.get = vi.fn().mockRejectedValue({
      response: { status: 304 },
    })

    const consoleError = vi.spyOn(console, 'error').mockImplementation(() => {})

    renderHook(() => useSastaPolling('game-123', 1000))

    await vi.runOnlyPendingTimersAsync()

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

    renderHook(() => useSastaPolling('game-123', 1000))

    await vi.runOnlyPendingTimersAsync()
    
    expect(mockSetError).toHaveBeenCalledWith('Server error')
    consoleError.mockRestore()
  })

  it('does not poll when gameId is null', async () => {
    renderHook(() => useSastaPolling(null, 1000))

    await vi.runOnlyPendingTimersAsync()

    expect(apiClient.get).not.toHaveBeenCalled()
  })

  it('polls at specified interval', async () => {
    renderHook(() => useSastaPolling('game-123', 1000))

    // Initial poll happens immediately
    await vi.runOnlyPendingTimersAsync()
    const initialCalls = apiClient.get.mock.calls.length
    expect(initialCalls).toBeGreaterThanOrEqual(1)

    // Advance timer by interval
    await vi.advanceTimersByTimeAsync(1000)
    expect(apiClient.get.mock.calls.length).toBeGreaterThan(initialCalls)
  })

  it('cleans up interval on unmount', async () => {
    const { unmount } = renderHook(() => useSastaPolling('game-123', 1000))

    // Initial poll
    await vi.runOnlyPendingTimersAsync()
    const callsBeforeUnmount = apiClient.get.mock.calls.length

    unmount()

    // Advance timer - should not poll after unmount
    await vi.advanceTimersByTimeAsync(2000)

    expect(apiClient.get).toHaveBeenCalledTimes(callsBeforeUnmount)
  })

  it('refetch function triggers immediate poll', async () => {
    const { result } = renderHook(() => useSastaPolling('game-123', 1000))

    // Initial poll
    await vi.runOnlyPendingTimersAsync()
    const initialCalls = apiClient.get.mock.calls.length

    // Call refetch
    await act(async () => {
      await result.current.refetch()
    })

    expect(apiClient.get).toHaveBeenCalledTimes(initialCalls + 1)
  })
})
