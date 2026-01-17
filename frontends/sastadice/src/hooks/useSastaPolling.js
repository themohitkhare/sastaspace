/**
 * Polling hook with version diffing to avoid unnecessary re-renders
 */
import { useEffect, useRef, useCallback } from 'react'
import { useGameStore } from '../store/useGameStore'
import { apiClient } from '../api/apiClient'

export function useSastaPolling(gameId, intervalMs = 2000) {
  const setGame = useGameStore((s) => s.setGame)
  const setError = useGameStore((s) => s.setError)
  const intervalRef = useRef(null)

  const fetchGameState = useCallback(async () => {
    if (!gameId) return

    try {
      // Get current version from store on each poll to avoid stale closures
      const currentVersion = useGameStore.getState().version

      const res = await apiClient.get(`/sastadice/games/${gameId}/state`, {
        params: { version: currentVersion },
        validateStatus: (status) => status === 200 || status === 304,
      })

      // 200 = new data, update state
      if (res.status === 200 && res.data) {
        setGame(res.data.game, res.data.version)
      }
      // 304 = no changes, skip update
    } catch (err) {
      if (err.response?.status !== 304) {
        setError(err.message)
      }
    }
  }, [gameId, setGame, setError])

  useEffect(() => {
    if (!gameId) return

    // Start polling
    intervalRef.current = setInterval(fetchGameState, intervalMs)
    fetchGameState() // Initial fetch immediately

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [gameId, intervalMs, fetchGameState])

  // Return refetch function for manual refresh
  return { refetch: fetchGameState }
}
