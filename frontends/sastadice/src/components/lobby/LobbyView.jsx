import React, { useState } from 'react'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'
import PlayerList from './PlayerList'

export default function LobbyView() {
  const [playerName, setPlayerName] = useState('')
  const [isJoining, setIsJoining] = useState(false)
  const [copied, setCopied] = useState(false)
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)
  const setPlayerId = useGameStore((s) => s.setPlayerId)
  const setGame = useGameStore((s) => s.setGame)

  const handleCopyGameId = async () => {
    if (gameId) {
      try {
        await navigator.clipboard.writeText(gameId)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      } catch (err) {
        console.error('Failed to copy game ID:', err)
        const textArea = document.createElement('textarea')
        textArea.value = gameId
        document.body.appendChild(textArea)
        textArea.select()
        document.execCommand('copy')
        document.body.removeChild(textArea)
        setCopied(true)
        setTimeout(() => setCopied(false), 2000)
      }
    }
  }

  const handleJoin = async () => {
    if (!playerName.trim()) {
      alert('Please enter your name')
      return
    }

    setIsJoining(true)

    try {
      const res = await apiClient.post(`/sastadice/games/${gameId}/join`, {
        name: playerName,
      })

      setPlayerId(res.data.id)
      
      const gameRes = await apiClient.get(`/sastadice/games/${gameId}/state`)
      if (gameRes.data) {
        setGame(gameRes.data.game, gameRes.data.version)
      }
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

      {gameId && (
        <div className="mb-6 border-brutal-lg bg-sasta-accent p-4 shadow-brutal-lg">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-zero mb-1 opacity-75">GAME ID (Share with players)</p>
              <p className="text-xl font-zero font-bold break-all">{gameId}</p>
            </div>
            <button
              onClick={handleCopyGameId}
              className="border-brutal-sm bg-sasta-black text-sasta-white px-4 py-2 font-zero font-bold shadow-brutal-sm hover:bg-sasta-white hover:text-sasta-black transition-colors whitespace-nowrap"
            >
              {copied ? 'COPIED!' : 'COPY'}
            </button>
          </div>
        </div>
      )}

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
            onKeyPress={(e) => {
              if (e.key === 'Enter' && playerName.trim() && !isJoining) {
                handleJoin()
              }
            }}
          />

          <button
            onClick={handleJoin}
            disabled={isJoining || !playerName.trim()}
            className="w-full border-brutal-sm bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50"
          >
            {isJoining ? 'JOINING...' : 'JOIN GAME'}
          </button>
          <p className="text-sm font-zero mt-3 opacity-75 text-center">
            Tiles will be automatically assigned
          </p>
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
