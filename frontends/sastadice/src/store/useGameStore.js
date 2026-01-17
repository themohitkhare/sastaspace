/**
 * Zustand store for game state management
 */
import { create } from 'zustand'

export const useGameStore = create((set, get) => ({
  // State
  gameId: null,
  playerId: null,
  game: null,
  version: 0,
  isLoading: false,
  error: null,

  // Actions
  setGame: (game, version) => set({ game, version, error: null }),
  setGameId: (gameId) => set({ gameId }),
  setPlayerId: (playerId) => set({ playerId }),
  setLoading: (isLoading) => set({ isLoading }),
  setError: (error) => set({ error }),

  // Computed selectors
  isMyTurn: () => {
    const { game, playerId } = get()
    return game?.current_turn_player_id === playerId
  },

  myPlayer: () => {
    const { game, playerId } = get()
    return game?.players?.find((p) => p.id === playerId)
  },

  getPlayerById: (id) => {
    const { game } = get()
    return game?.players?.find((p) => p.id === id)
  },

  reset: () => set({
    gameId: null,
    playerId: null,
    game: null,
    version: 0,
    isLoading: false,
    error: null,
  }),
}))
