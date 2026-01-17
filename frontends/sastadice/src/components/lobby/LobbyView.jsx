import { useState } from 'react'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'
import LaunchKey from './LaunchKey'
import KeyStatus from './KeyStatus'

export default function LobbyView({ onRefresh }) {
  const [playerName, setPlayerName] = useState('')
  const [isJoining, setIsJoining] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [copied, setCopied] = useState(false)
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)
  const playerId = useGameStore((s) => s.playerId)
  const setPlayerId = useGameStore((s) => s.setPlayerId)
  const setGame = useGameStore((s) => s.setGame)

  const handleCopyGameId = async () => {
    if (!gameId) return
    try {
      await navigator.clipboard.writeText(gameId)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
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

  const handleJoin = async () => {
    if (!playerName.trim()) {
      alert('Please enter your name')
      return
    }
    setIsJoining(true)
    try {
      const res = await apiClient.post(`/sastadice/games/${gameId}/join`, { name: playerName })
      setPlayerId(res.data.id)
      const gameRes = await apiClient.get(`/sastadice/games/${gameId}/state`)
      if (gameRes.data) setGame(gameRes.data.game, gameRes.data.version)
    } catch {
      alert('Failed to join game')
    } finally {
      setIsJoining(false)
    }
  }

  const handleToggleReady = async () => {
    if (!playerId) return
    setIsToggling(true)
    try {
      await apiClient.post(`/sastadice/games/${gameId}/ready/${playerId}`)
      if (onRefresh) onRefresh()
    } catch {
      alert('Failed to toggle ready')
    } finally {
      setIsToggling(false)
    }
  }

  const myPlayer = game?.players?.find((p) => p.id === playerId)
  const otherPlayers = game?.players?.filter((p) => p.id !== playerId) || []
  const hasJoined = !!myPlayer
  const allReady = game?.players?.length > 0 && game?.players?.every((p) => p.ready)
  const readyCount = game?.players?.filter((p) => p.ready).length || 0
  const totalPlayers = game?.players?.length || 0

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h2 className="text-5xl font-bold font-zero mb-8">GAME LOBBY</h2>

      {gameId && (
        <div className="mb-8 border-brutal-lg bg-sasta-accent p-6 shadow-brutal-lg">
          <div className="flex items-center justify-between gap-4">
            <div className="flex-1">
              <p className="text-sm font-zero font-bold mb-2 opacity-75">GAME CODE (SHARE WITH PLAYERS)</p>
              <p className="text-lg font-zero font-bold break-all font-mono">{gameId}</p>
            </div>
            <button
              onClick={handleCopyGameId}
              className="border-brutal-sm bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-white hover:text-sasta-black transition-colors whitespace-nowrap"
            >
              {copied ? 'COPIED!' : 'COPY'}
            </button>
          </div>
        </div>
      )}

      {!hasJoined ? (
        <div className="border-brutal-lg bg-sasta-white p-6 shadow-brutal-lg">
          <h3 className="text-2xl font-bold font-zero mb-4">JOIN GAME</h3>
          <input
            type="text"
            value={playerName}
            onChange={(e) => setPlayerName(e.target.value)}
            placeholder="Enter your name"
            className="w-full p-4 border-brutal-sm mb-4 font-zero text-lg"
            onKeyPress={(e) => {
              if (e.key === 'Enter' && playerName.trim() && !isJoining) handleJoin()
            }}
          />
          <button
            onClick={handleJoin}
            disabled={isJoining || !playerName.trim()}
            className="w-full border-brutal-sm bg-sasta-accent text-sasta-black px-6 py-4 font-zero font-bold text-lg shadow-brutal-sm hover:bg-sasta-black hover:text-sasta-accent transition-colors disabled:opacity-50"
          >
            {isJoining ? '> JOINING...' : '> JOIN GAME'}
          </button>
          <p className="text-sm font-zero mt-3 opacity-75 text-center">TILES WILL BE AUTO-ASSIGNED</p>
          
          {totalPlayers > 0 && (
            <div className="mt-6 pt-6 border-t-2 border-sasta-black">
              <p className="font-zero text-sm mb-3">WAITING IN LOBBY ({totalPlayers}):</p>
              <div className="space-y-2">
                {game?.players?.map((p) => (
                  <KeyStatus key={p.id} player={p} isMe={false} />
                ))}
              </div>
            </div>
          )}
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Launch Control Panel */}
          <div className="border-brutal-lg bg-zinc-900 p-6 shadow-brutal-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="font-zero text-lg font-bold text-zinc-300">LAUNCH CONTROL</h3>
              <div className="font-zero text-sm text-zinc-500">
                {readyCount}/{totalPlayers} ARMED
              </div>
            </div>

            <LaunchKey
              isReady={myPlayer?.ready || false}
              isLoading={isToggling}
              onToggle={handleToggleReady}
              playerName={myPlayer?.name}
              playerColor={myPlayer?.color}
            />

            {allReady && (
              <div className="mt-4 p-4 bg-green-500/20 border-2 border-green-500 animate-pulse">
                <p className="font-zero font-bold text-center text-green-400">
                  🚀 ALL KEYS ARMED - INITIATING LAUNCH SEQUENCE 🚀
                </p>
              </div>
            )}

            <p className="text-sm font-zero mt-4 text-zinc-500 text-center">
              {totalPlayers === 1
                ? 'CPU OPERATOR WILL BE ASSIGNED ON LAUNCH'
                : `${totalPlayers} OPERATORS IN CONTROL ROOM`}
            </p>
          </div>

          {/* Operator Status Panel */}
          <div className="border-brutal-lg bg-sasta-white p-6 shadow-brutal-lg">
            <h3 className="text-lg font-bold font-zero mb-4">OPERATOR STATUS</h3>
            
            {/* My status */}
            {myPlayer && (
              <div className="mb-4">
                <p className="font-zero text-xs text-zinc-500 mb-2">YOUR STATION</p>
                <KeyStatus player={myPlayer} isMe={true} />
              </div>
            )}

            {/* Other players */}
            {otherPlayers.length > 0 && (
              <div>
                <p className="font-zero text-xs text-zinc-500 mb-2">OTHER OPERATORS ({otherPlayers.length})</p>
                <div className="space-y-2">
                  {otherPlayers.map((p) => (
                    <KeyStatus key={p.id} player={p} isMe={false} />
                  ))}
                </div>
              </div>
            )}

            {otherPlayers.length === 0 && (
              <div className="text-center py-8 border-2 border-dashed border-zinc-300">
                <p className="font-zero text-zinc-500">WAITING FOR OTHER OPERATORS...</p>
                <p className="font-zero text-xs text-zinc-400 mt-2">Share the game code to invite players</p>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
