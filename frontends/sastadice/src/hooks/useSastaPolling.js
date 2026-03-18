import { useEffect, useRef, useCallback, useState } from 'react'
import { useGameStore } from '../store/useGameStore'
import { apiClient } from '../api/apiClient'

const CONNECTION_LOSS_THRESHOLD = 3

export function useSastaPolling(gameId, intervalMs = 2000) {
  const setGame = useGameStore((s) => s.setGame)
  const setError = useGameStore((s) => s.setError)
  const intervalRef = useRef(null)
  const consecutiveFailuresRef = useRef(0)
  const [connectionLost, setConnectionLost] = useState(false)

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

      // Reset failure tracking on success
      consecutiveFailuresRef.current = 0
      if (connectionLost) {
        setConnectionLost(false)
        setError(null)
      }
    } catch (err) {
      if (err.response?.status !== 304) {
        consecutiveFailuresRef.current += 1
        if (consecutiveFailuresRef.current >= CONNECTION_LOSS_THRESHOLD) {
          setConnectionLost(true)
        }
        setError(err.message)
      }
    }
  }, [gameId, setGame, setError, connectionLost])

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

  const retry = useCallback(() => {
    consecutiveFailuresRef.current = 0
    setConnectionLost(false)
    fetchGameState()
  }, [fetchGameState])

  return { refetch: fetchGameState, connectionLost, retry }
}
