import { useState, useEffect } from 'react'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'
import LaunchKey from './LaunchKey'
import KeyStatus from './KeyStatus'
import GameSettingsPanel from './GameSettingsPanel'

export default function LobbyView({ onRefresh }) {
  const [playerName, setPlayerName] = useState('')
  const [isJoining, setIsJoining] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [isUpdatingSettings, setIsUpdatingSettings] = useState(false)
  const [copied, setCopied] = useState(false)
  const [settings, setSettings] = useState({
    win_condition: 'SUDDEN_DEATH',
    round_limit: 30,
    chaos_level: 'NORMAL',
    doubles_give_extra_turn: true,
    enable_stimulus: true,
    enable_black_market: true,
    enable_auctions: true,
    target_cash: 10000,
  })
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)
  const playerId = useGameStore((s) => s.playerId)
  const setPlayerId = useGameStore((s) => s.setPlayerId)
  const setGame = useGameStore((s) => s.setGame)

  // Load settings from game state
  useEffect(() => {
    if (game?.settings && !isUpdatingSettings) {
      setSettings(game.settings)
    }
  }, [game?.settings, isUpdatingSettings])

  const handleUpdateSettings = async (newSettings) => {
    setSettings(newSettings)
    setIsUpdatingSettings(true)
    // Send to backend
    try {
      await apiClient.patch(`/sastadice/games/${gameId}/settings`, {
        host_id: playerId,
        settings: newSettings,
      })
      if (onRefresh) await onRefresh()
    } catch (err) {
      console.error('Failed to update settings:', err)
      // Revert from game state if failed
      if (game?.settings) setSettings(game.settings)
    } finally {
      setIsUpdatingSettings(false)
    }
  }

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

  const handleKickPlayer = async (targetPlayerId) => {
    if (!playerId || !game?.host_id) return
    if (!confirm('Are you sure you want to kick this player?')) return

    try {
      await apiClient.delete(`/sastadice/games/${gameId}/players/${targetPlayerId}?host_id=${playerId}`)
      if (onRefresh) onRefresh()
    } catch {
      alert('Failed to kick player')
    }
  }

  const myPlayer = game?.players?.find((p) => p.id === playerId)
  const otherPlayers = game?.players?.filter((p) => p.id !== playerId) || []
  const hasJoined = !!myPlayer
  const allReady = game?.players?.length > 0 && game?.players?.every((p) => p.ready)
  const readyCount = game?.players?.filter((p) => p.ready).length || 0
  const totalPlayers = game?.players?.length || 0
  const isHost = game?.host_id === playerId
  const shortCode = gameId?.slice(0, 8)?.toUpperCase() || 'LOADING'

  return (
    <div className="h-screen bg-sasta-white flex flex-col lg:flex-row p-4 gap-4 overflow-hidden">
      <div className="lg:w-[360px] flex flex-col gap-4 shrink-0">
        <h1 className="text-3xl lg:text-4xl font-bold font-zero">GAME LOBBY</h1>

        {gameId && (
          <div className="bg-sasta-black text-sasta-accent p-4 border-brutal shadow-brutal">
            <div className="text-[10px] font-data uppercase opacity-60 text-sasta-white mb-1">ACCESS CODE</div>
            <div className="flex justify-between items-center gap-3">
              <span className="text-2xl lg:text-3xl font-data font-bold tracking-wider">{shortCode}</span>
              <button
                onClick={handleCopyGameId}
                className="bg-sasta-accent text-sasta-black px-4 py-2 font-data font-bold text-sm hover:bg-white transition-colors"
              >
                {copied ? '✓ COPIED' : 'COPY'}
              </button>
            </div>
          </div>
        )}

        {!hasJoined && (
          <div className="border-2 border-sasta-black p-3 bg-white">
            <div className="text-xs font-data font-bold mb-2 opacity-60">&gt; AUTHENTICATE PLAYER</div>
            <div className="flex gap-2">
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="ENTER_NAME"
                className="flex-1 bg-gray-100 border-b-2 border-sasta-black p-2 font-data text-sm focus:outline-none focus:bg-sasta-accent/20"
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && playerName.trim() && !isJoining) handleJoin()
                }}
              />
              <button
                onClick={handleJoin}
                disabled={isJoining || !playerName.trim()}
                className="bg-sasta-black text-sasta-white px-4 py-2 font-data font-bold text-sm hover:bg-gray-800 transition-colors disabled:opacity-50"
              >
                {isJoining ? '...' : 'ENTER'}
              </button>
            </div>
          </div>
        )}

        {hasJoined && (
          <>
            <GameSettingsPanel
              settings={settings}
              onUpdate={handleUpdateSettings}
              isHost={isHost}
            />

            <div className="bg-zinc-900 p-4 border-brutal shadow-brutal flex-1 flex flex-col">
              <div className="flex items-center justify-between mb-3">
                <h3 className="font-data text-sm font-bold text-zinc-300">LAUNCH CONTROL</h3>
                <div className="font-data text-xs text-zinc-500">
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
                <div className="mt-3 p-3 bg-green-500/20 border border-green-500 animate-pulse">
                  <p className="font-data font-bold text-center text-green-400 text-sm">
                    🚀 ALL ARMED - LAUNCHING...
                  </p>
                </div>
              )}

              <p className="text-xs font-data mt-auto pt-3 text-zinc-500 text-center">
                {totalPlayers === 1 ? 'CPU JOINS ON LAUNCH' : `${totalPlayers} OPERATORS`}
              </p>
            </div>
          </>
        )}
      </div>

      <div className="flex-1 border-brutal bg-white p-4 flex flex-col min-h-0 overflow-hidden">
        <div className="flex justify-between items-center mb-3 border-b-2 border-sasta-black pb-2 shrink-0">
          <div className="font-data font-bold text-base">CONNECTED_PLAYERS ({totalPlayers})</div>
          <div className="flex items-center gap-2">
            <div className="animate-pulse w-2 h-2 bg-green-500 rounded-full"></div>
            <span className="text-xs font-data text-zinc-500">LIVE</span>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto space-y-2 pr-1">
          {myPlayer && (
            <div className="flex items-center gap-3 p-3 border-2 border-sasta-black bg-sasta-accent/20">
              <div
                className="w-10 h-10 rounded-full border-2 border-sasta-black flex items-center justify-center font-data font-bold text-white text-lg"
                style={{ backgroundColor: myPlayer.color }}
              >
                {myPlayer.name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-data font-bold text-base leading-none truncate">
                  {myPlayer.name?.toUpperCase()} {isHost && '👑'}
                </div>
                <div className={`text-xs font-data mt-0.5 ${myPlayer.ready ? 'text-green-600' : 'text-orange-600'}`}>
                  {myPlayer.ready ? 'READY' : 'NOT READY'}
                </div>
              </div>
              <div className="text-xs font-data bg-sasta-black text-sasta-accent px-2 py-1">YOU</div>
            </div>
          )}

          {otherPlayers.map((p) => (
            <div key={p.id} className="flex items-center gap-3 p-3 border-2 border-sasta-black">
              <div
                className="w-10 h-10 rounded-full border-2 border-sasta-black flex items-center justify-center font-data font-bold text-white text-lg"
                style={{ backgroundColor: p.color }}
              >
                {p.name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="font-data font-bold text-base leading-none truncate">
                  {p.name?.toUpperCase()} {p.id === game?.host_id && '👑'}
                </div>
                <div className={`text-xs font-data mt-0.5 ${p.ready ? 'text-green-600' : 'text-orange-600'}`}>
                  {p.ready ? 'READY' : 'NOT READY'}
                </div>
              </div>
              {isHost && (
                <button
                  onClick={() => handleKickPlayer(p.id)}
                  className="text-xs font-data text-red-500 hover:text-red-700 px-2 py-1 border border-red-500 hover:bg-red-50"
                >
                  KICK
                </button>
              )}
            </div>
          ))}

          {totalPlayers === 0 && (
            <div className="text-center py-8 border-2 border-dashed border-zinc-300">
              <p className="font-data text-zinc-500">WAITING FOR PLAYERS...</p>
              <p className="font-data text-xs text-zinc-400 mt-1">Share the code above</p>
            </div>
          )}

          {hasJoined && otherPlayers.length === 0 && (
            <div className="text-center py-6 border-2 border-dashed border-zinc-300">
              <p className="font-data text-zinc-500 text-sm">WAITING FOR OPERATORS...</p>
              <p className="font-data text-xs text-zinc-400 mt-1">Share code: {shortCode}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
