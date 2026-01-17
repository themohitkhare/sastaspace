/**
 * LobbyView - Game lobby where players join and submit tiles
 */
import React, { useState } from 'react'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'
import TileSubmissionForm from './TileSubmissionForm'
import PlayerList from './PlayerList'

export default function LobbyView() {
  const [playerName, setPlayerName] = useState('')
  const [tiles, setTiles] = useState([])
  const [isJoining, setIsJoining] = useState(false)
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)
  const setPlayerId = useGameStore((s) => s.setPlayerId)

  const handleJoin = async () => {
    if (!playerName || tiles.length !== 5) {
      alert('Please enter your name and submit 5 tiles')
      return
    }

    setIsJoining(true)

    try {
      const res = await apiClient.post(`/sastadice/games/${gameId}/join`, {
        name: playerName,
        tiles,
      })

      setPlayerId(res.data.id)
    } catch (err) {
      console.error('Error joining game:', err)
      alert('Failed to join game')
    } finally {
      setIsJoining(false)
    }
  }

  const handleStart = async () => {
    try {
      await apiClient.post(`/sastadice/games/${gameId}/start`)
    } catch (err) {
      console.error('Error starting game:', err)
      alert('Failed to start game')
    }
  }

  const canStart = game?.status === 'LOBBY' && game?.players?.length >= 2

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h2 className="text-4xl font-bold font-zero mb-6">GAME LOBBY</h2>

      <PlayerList players={game?.players || []} />

      {(() => {
        const playerId = useGameStore.getState().playerId
        return !game?.players?.find((p) => p.id === playerId)
      })() ? (
        <div className="mt-8 border-brutal-lg bg-sasta-white p-6 shadow-brutal-lg">
          <h3 className="text-2xl font-bold font-zero mb-4">JOIN GAME</h3>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Enter your name"
            className="w-full p-3 border-brutal-sm mb-4 font-zero"
          />

          <TileSubmissionForm tiles={tiles} setTiles={setTiles} />

          <button
            onClick={handleJoin}
            disabled={isJoining || tiles.length !== 5}
            className="mt-4 border-brutal-sm bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50"
          >
            {isJoining ? 'JOINING...' : 'JOIN GAME'}
          </button>
        </div>
      ) : (
        <div className="mt-8 border-brutal-lg bg-sasta-white p-6 shadow-brutal-lg">
          <p className="font-zero mb-4">Waiting for other players...</p>
          {canStart && (
            <button
              onClick={handleStart}
              className="border-brutal-sm bg-sasta-accent text-sasta-black px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-black hover:text-sasta-white transition-colors"
            >
              START GAME
            </button>
          )}
        </div>
      )}
    </div>
  )
}
