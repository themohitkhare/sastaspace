import { create } from 'zustand'
import { persist } from 'zustand/middleware'

export const useGameStore = create(
  persist(
    (set, get) => ({
      gameId: null,
      playerId: null,
      game: null,
      version: 0,
      isLoading: false,
      error: null,
      lastRestoredAt: 0,

      setGame: (game, version) => set({ game, version, error: null }),
      setGameId: (gameId) => set({ gameId }),
      setPlayerId: (playerId) => set({ playerId }),
      setLoading: (isLoading) => set({ isLoading }),
      setError: (error) => set({ error }),
      setLastRestoredAt: (ts) => set({ lastRestoredAt: ts }),

      isMyTurn: () => {
        const { game, playerId } = get()
        return game?.current_turn_player_id === playerId
      },

      myPlayer: () => {
        const { game, playerId } = get()
        return game?.players?.find((p) => p.id === playerId)
      },

      currentTurnPlayer: () => {
        const { game } = get()
        return game?.players?.find((p) => p.id === game?.current_turn_player_id)
      },

      turnPhase: () => {
        const { game } = get()
        return game?.turn_phase || 'PRE_ROLL'
      },

      pendingDecision: () => {
        const { game } = get()
        return game?.pending_decision
      },

      getPlayerById: (id) => {
        const { game } = get()
        return game?.players?.find((p) => p.id === id)
      },

      getTileById: (id) => {
        const { game } = get()
        return game?.board?.find((t) => t.id === id)
      },

      reset: () => set({
        gameId: null,
        playerId: null,
        game: null,
        version: 0,
        isLoading: false,
        error: null,
        lastRestoredAt: 0,
      }),
    }),
    {
      name: 'sastadice-game-store',
      partialize: (state) => ({
        gameId: state.gameId,
        playerId: state.playerId,
      }),
    }
  )
)
