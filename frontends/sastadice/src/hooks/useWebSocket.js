import { useEffect, useRef, useState, useCallback } from 'react'
import { useGameStore } from '../store/useGameStore'
import { useSastaPolling } from './useSastaPolling'

const MAX_RECONNECT_DELAY = 8000
const MAX_FAILURES = 3

function getWsUrl(gameId) {
  const loc = window.location
  const protocol = loc.protocol === 'https:' ? 'wss:' : 'ws:'

  // When served through Traefik (port 80/443), use relative path
  if (loc.hostname === 'localhost' || loc.hostname === '127.0.0.1') {
    if (!loc.port || loc.port === '80' || loc.port === '443') {
      return `${protocol}//${loc.host}/api/v1/sastadice/games/${gameId}/ws`
    }
    return `ws://localhost:8000/api/v1/sastadice/games/${gameId}/ws`
  }
  return `${protocol}//${loc.hostname}:8000/api/v1/sastadice/games/${gameId}/ws`
}

export function useWebSocket(gameId, playerId) {
  const setGame = useGameStore((s) => s.setGame)
  const wsRef = useRef(null)
  const reconnectTimeoutRef = useRef(null)
  const failureCountRef = useRef(0)
  const [connected, setConnected] = useState(false)
  const [useFallback, setUseFallback] = useState(false)

  // Polling fallback — only active when WS fails
  const polling = useSastaPolling(useFallback ? gameId : null, 1500)

  const connect = useCallback(() => {
    if (!gameId || useFallback) return
    if (wsRef.current?.readyState === WebSocket.OPEN) return

    try {
      const ws = new WebSocket(getWsUrl(gameId))
      wsRef.current = ws

      ws.onopen = () => {
        setConnected(true)
        failureCountRef.current = 0
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'STATE_UPDATE' && msg.game) {
            setGame(msg.game, msg.version)
          }
        } catch {
          // ignore parse errors
        }
      }

      ws.onclose = () => {
        setConnected(false)
        wsRef.current = null
        failureCountRef.current += 1

        if (failureCountRef.current >= MAX_FAILURES) {
          setUseFallback(true)
          return
        }

        // Exponential backoff reconnect
        const delay = Math.min(1000 * Math.pow(2, failureCountRef.current - 1), MAX_RECONNECT_DELAY)
        reconnectTimeoutRef.current = setTimeout(connect, delay)
      }

      ws.onerror = () => {
        // onclose will fire after onerror
      }
    } catch {
      failureCountRef.current += 1
      if (failureCountRef.current >= MAX_FAILURES) {
        setUseFallback(true)
      }
    }
  }, [gameId, useFallback, setGame])

  useEffect(() => {
    connect()

    return () => {
      if (reconnectTimeoutRef.current) {
        clearTimeout(reconnectTimeoutRef.current)
      }
      if (wsRef.current) {
        wsRef.current.close()
        wsRef.current = null
      }
    }
  }, [connect])

  // Keep-alive ping every 30s
  useEffect(() => {
    if (!connected) return
    const interval = setInterval(() => {
      if (wsRef.current?.readyState === WebSocket.OPEN) {
        wsRef.current.send('ping')
      }
    }, 30000)
    return () => clearInterval(interval)
  }, [connected])

  const refetch = useCallback(() => {
    // Manual refetch for action callbacks — just ping the WS to acknowledge
    // The server will broadcast state after any mutation anyway
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send('refetch')
    }
    // Also call polling refetch as fallback
    if (useFallback) {
      polling.refetch()
    }
  }, [useFallback, polling])

  return {
    connected: connected || (useFallback && !polling.connectionLost),
    connectionLost: !connected && (useFallback ? polling.connectionLost : failureCountRef.current > 0),
    refetch,
    retry: useCallback(() => {
      failureCountRef.current = 0
      setUseFallback(false)
      setConnected(false)
      connect()
    }, [connect]),
  }
}
