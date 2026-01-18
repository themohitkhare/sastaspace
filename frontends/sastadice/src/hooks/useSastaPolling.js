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
      const currentVersion = useGameStore.getState().version

      const res = await apiClient.get(`/sastadice/games/${gameId}/state`, {
        params: { version: currentVersion },
        validateStatus: (status) => status === 200 || status === 304,
      })

      if (res.status === 200 && res.data) {
        setGame(res.data.game, res.data.version)
      }
    } catch (err) {
      if (err.response?.status !== 304) {
        setError(err.message)
      }
    }
  }, [gameId, setGame, setError])

  useEffect(() => {
    if (!gameId) return

    intervalRef.current = setInterval(fetchGameState, intervalMs)
    fetchGameState()

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [gameId, intervalMs, fetchGameState])

  return { refetch: fetchGameState }
}
