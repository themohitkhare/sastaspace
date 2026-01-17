/**
 * LobbyPage - Game lobby page
 */
import React from 'react'
import { useSastaPolling } from '../hooks/useSastaPolling'
import { useGameStore } from '../store/useGameStore'
import LobbyView from '../components/lobby/LobbyView'

export default function LobbyPage() {
  const gameId = useGameStore((s) => s.gameId)

  // Start polling for lobby updates
  const { refetch } = useSastaPolling(gameId, 2000)

  return (
    <div className="min-h-screen bg-sasta-white">
      <LobbyView onRefresh={refetch} />
    </div>
  )
}
