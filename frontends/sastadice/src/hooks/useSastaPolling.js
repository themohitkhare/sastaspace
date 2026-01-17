/**
 * Polling hook with version diffing to avoid unnecessary re-renders
 */
import { useEffect, useRef } from 'react'
import { useGameStore } from '../store/useGameStore'
import { apiClient } from '../api/apiClient'

export function useSastaPolling(gameId, intervalMs = 2000) {
  const setGame = useGameStore((s) => s.setGame)
  const setError = useGameStore((s) => s.setError)
  const intervalRef = useRef(null)

  useEffect(() => {
    if (!gameId) return

    const poll = async () => {
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
        // Only log if it's not a 304 Not Modified
        if (err.response?.status !== 304) {
          console.error('Polling error:', err)
          setError(err.message)
        }
      }
    }

    // Start polling
    intervalRef.current = setInterval(poll, intervalMs)
    poll() // Initial fetch immediately

    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [gameId, intervalMs, setGame, setError])
}
