import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'

// Mock the store
const mockStore = {
  gameId: 'test-game',
  playerId: 'player-1',
  game: null,
  version: 0,
  isLoading: false,
  error: null,
  lastRestoredAt: 0,
  setGame: vi.fn(),
  setPlayerId: vi.fn(),
  setGameId: vi.fn(),
  setLastRestoredAt: vi.fn(),
  reset: vi.fn(),
  isMyTurn: vi.fn(() => false),
  myPlayer: vi.fn(() => null),
  currentTurnPlayer: vi.fn(() => null),
  turnPhase: vi.fn(() => 'PRE_ROLL'),
  getTileById: vi.fn(),
  getPlayerById: vi.fn(),
}

vi.mock('../../src/store/useGameStore', () => ({
  useGameStore: (selector) => selector(mockStore),
}))

vi.mock('../../src/api/apiClient', () => ({
  apiClient: {
    get: vi.fn(),
  },
}))

import { apiClient } from '../../src/api/apiClient'
import App from '../../src/App'

describe('GameRoute session restoration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockStore.game = null
    mockStore.gameId = 'test-game'
    mockStore.playerId = 'player-1'
    mockStore.lastRestoredAt = 0
  })

  it('redirects to home when restored game is FINISHED and player not found', async () => {
    apiClient.get.mockResolvedValue({
      data: {
        game: {
          id: 'test-game',
          status: 'FINISHED',
          players: [{ id: 'other-player', name: 'Other' }],
          board: [],
        },
        version: 1,
      },
    })

    window.history.pushState({}, 'Test page', '/sastadice/game/test-game')
    render(<App />)

    await waitFor(() => {
      expect(mockStore.setPlayerId).toHaveBeenCalledWith(null)
    })
    expect(mockStore.reset).toHaveBeenCalled()
  })

  it('cancels fetch on unmount via AbortController', async () => {
    let resolveFn
    apiClient.get.mockImplementation(() => new Promise((resolve) => { resolveFn = resolve }))

    window.history.pushState({}, 'Test page', '/sastadice/game/test-game')
    const { unmount } = render(<App />)

    unmount()

    // Resolve the promise AFTER unmount
    resolveFn({
      data: {
        game: { id: 'test-game', status: 'ACTIVE', players: [], board: [] },
        version: 1,
      },
    })

    // Wait a tick for the .then to execute
    await new Promise(r => setTimeout(r, 0))

    // AbortController should have prevented the state update
    expect(mockStore.setGame).not.toHaveBeenCalled()
  })
})
