/**
 * LobbyPage - Game lobby page
 */
import React from 'react'
import { useWebSocket } from '../hooks/useWebSocket'
import { useGameStore } from '../store/useGameStore'
import LobbyView from '../components/lobby/LobbyView'

export default function LobbyPage() {
  const gameId = useGameStore((s) => s.gameId)
  const playerId = useGameStore((s) => s.playerId)
  const { refetch } = useWebSocket(gameId, playerId)

  return (
    <div className="min-h-screen bg-sasta-white">
      <LobbyView onRefresh={refetch} />
    </div>
  )
}
