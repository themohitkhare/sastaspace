/**
 * Tests for useGameStore
 */
import { describe, it, expect, beforeEach } from 'vitest'
import { useGameStore } from '../../src/store/useGameStore'

describe('useGameStore', () => {
  beforeEach(() => {
    // Reset store before each test
    useGameStore.getState().reset()
  })

  it('initializes with default values', () => {
    const state = useGameStore.getState()
    expect(state.gameId).toBeNull()
    expect(state.playerId).toBeNull()
    expect(state.game).toBeNull()
    expect(state.version).toBe(0)
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })

  it('sets game ID', () => {
    useGameStore.getState().setGameId('game-123')
    expect(useGameStore.getState().gameId).toBe('game-123')
  })

  it('sets player ID', () => {
    useGameStore.getState().setPlayerId('player-123')
    expect(useGameStore.getState().playerId).toBe('player-123')
  })

  it('sets game and version', () => {
    const mockGame = {
      id: 'game-123',
      status: 'ACTIVE',
      players: [],
      board: [],
    }
    useGameStore.getState().setGame(mockGame, 5)
    const state = useGameStore.getState()
    expect(state.game).toEqual(mockGame)
    expect(state.version).toBe(5)
    expect(state.error).toBeNull()
  })

  it('sets loading state', () => {
    useGameStore.getState().setLoading(true)
    expect(useGameStore.getState().isLoading).toBe(true)
    useGameStore.getState().setLoading(false)
    expect(useGameStore.getState().isLoading).toBe(false)
  })

  it('sets error', () => {
    const error = 'Test error'
    useGameStore.getState().setError(error)
    expect(useGameStore.getState().error).toBe(error)
  })

  it('computes isMyTurn correctly', () => {
    const mockGame = {
      id: 'game-123',
      current_turn_player_id: 'player-123',
    }
    useGameStore.getState().setGame(mockGame, 1)
    useGameStore.getState().setPlayerId('player-123')
    expect(useGameStore.getState().isMyTurn()).toBe(true)

    useGameStore.getState().setPlayerId('player-456')
    expect(useGameStore.getState().isMyTurn()).toBe(false)
  })

  it('returns null for isMyTurn when game or playerId is missing', () => {
    expect(useGameStore.getState().isMyTurn()).toBe(false)

    useGameStore.getState().setPlayerId('player-123')
    expect(useGameStore.getState().isMyTurn()).toBe(false)

    useGameStore.getState().reset()
    const mockGame = {
      id: 'game-123',
      current_turn_player_id: 'player-123',
    }
    useGameStore.getState().setGame(mockGame, 1)
    expect(useGameStore.getState().isMyTurn()).toBe(false)
  })

  it('finds my player', () => {
    const mockPlayers = [
      { id: 'player-1', name: 'Player 1' },
      { id: 'player-123', name: 'Player 2' },
    ]
    const mockGame = {
      id: 'game-123',
      players: mockPlayers,
    }
    useGameStore.getState().setGame(mockGame, 1)
    useGameStore.getState().setPlayerId('player-123')
    const myPlayer = useGameStore.getState().myPlayer()
    expect(myPlayer).toEqual(mockPlayers[1])
  })

  it('returns null for myPlayer when not found', () => {
    const mockPlayers = [
      { id: 'player-1', name: 'Player 1' },
    ]
    const mockGame = {
      id: 'game-123',
      players: mockPlayers,
    }
    useGameStore.getState().setGame(mockGame, 1)
    useGameStore.getState().setPlayerId('player-999')
    const myPlayer = useGameStore.getState().myPlayer()
    expect(myPlayer).toBeUndefined()
  })

  it('finds player by ID', () => {
    const mockPlayers = [
      { id: 'player-1', name: 'Player 1' },
      { id: 'player-2', name: 'Player 2' },
    ]
    const mockGame = {
      id: 'game-123',
      players: mockPlayers,
    }
    useGameStore.getState().setGame(mockGame, 1)
    const player = useGameStore.getState().getPlayerById('player-2')
    expect(player).toEqual(mockPlayers[1])
  })

  it('returns undefined for getPlayerById when not found', () => {
    const mockPlayers = [
      { id: 'player-1', name: 'Player 1' },
    ]
    const mockGame = {
      id: 'game-123',
      players: mockPlayers,
    }
    useGameStore.getState().setGame(mockGame, 1)
    const player = useGameStore.getState().getPlayerById('player-999')
    expect(player).toBeUndefined()
  })

  it('resets store to initial state', () => {
    useGameStore.getState().setGameId('game-123')
    useGameStore.getState().setPlayerId('player-123')
    useGameStore.getState().setGame({ id: 'game-123' }, 5)
    useGameStore.getState().setLoading(true)
    useGameStore.getState().setError('Error')

    useGameStore.getState().reset()

    const state = useGameStore.getState()
    expect(state.gameId).toBeNull()
    expect(state.playerId).toBeNull()
    expect(state.game).toBeNull()
    expect(state.version).toBe(0)
    expect(state.isLoading).toBe(false)
    expect(state.error).toBeNull()
  })
})
