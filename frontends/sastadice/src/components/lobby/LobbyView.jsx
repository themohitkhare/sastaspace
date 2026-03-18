import { useState, useEffect } from 'react'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'
import LaunchKey from './LaunchKey'
import GameSettingsPanel from './GameSettingsPanel'
import RulesModal from '../RulesModal'
import { useToast } from '../../hooks/useToast'
import ToastContainer from '../ToastContainer'

export default function LobbyView({ onRefresh }) {
  const [playerName, setPlayerName] = useState('')
  const [isJoining, setIsJoining] = useState(false)
  const [isToggling, setIsToggling] = useState(false)
  const [hasChanges, setHasChanges] = useState(false)
  const [copied, setCopied] = useState(false)
  const [showRules, setShowRules] = useState(false)
  const { toasts, showToast, dismissToast } = useToast()
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

  useEffect(() => {
    if (game?.settings && !hasChanges) {
      setSettings(game.settings)
    }
  }, [game?.settings, hasChanges])

  const handleUpdateSettings = (newSettings) => {
    setSettings(newSettings)
    setHasChanges(true)
  }

  const handleSaveSettings = async () => {
    try {
      await apiClient.patch(`/sastadice/games/${gameId}/settings`, {
        host_id: playerId,
        settings: settings,
      })
      setHasChanges(false)
      if (onRefresh) await onRefresh()
    } catch (err) {
      showToast('Failed to save settings')
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
      showToast('Please enter your name', 'info')
      return
    }
    setIsJoining(true)
    try {
      const res = await apiClient.post(`/sastadice/games/${gameId}/join`, { name: playerName })
      setPlayerId(res.data.id)
      const gameRes = await apiClient.get(`/sastadice/games/${gameId}/state`)
      if (gameRes.data) setGame(gameRes.data.game, gameRes.data.version)
    } catch {
      showToast('Failed to join game')
    } finally {
      setIsJoining(false)
    }
  }

  const handleToggleReady = async () => {
    if (!playerId) return
    setIsToggling(true)
    try {
      if (isHost && hasChanges) {
        await handleSaveSettings()
      }

      await apiClient.post(`/sastadice/games/${gameId}/ready/${playerId}`)
      if (onRefresh) await onRefresh()
    } catch {
      showToast(hasChanges ? 'Failed to save settings and toggle ready' : 'Failed to toggle ready')
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
      showToast('Failed to kick player')
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
    <div className="h-screen w-full bg-white text-black overflow-hidden flex flex-col lg:grid lg:grid-cols-12 divide-y lg:divide-y-0 lg:divide-x divide-black">
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <div className="lg:col-span-3 p-6 flex flex-col gap-6 bg-white overflow-y-auto z-10">
        <div className="flex items-center justify-between">
          <h1 className="text-4xl font-black font-zero tracking-tighter">SASTADICE</h1>
          <button
            onClick={() => setShowRules(true)}
            className="bg-black text-white px-3 py-1 font-data font-bold text-xs hover:bg-gray-800 transition-colors"
          >
            REQ_INTEL
          </button>
        </div>

        {gameId && (
          <div className="bg-black p-6 relative overflow-hidden group">
            <div className="absolute top-0 right-0 w-16 h-16 bg-sasta-accent/20 rounded-bl-full transform translate-x-8 -translate-y-8 group-hover:bg-sasta-accent/40 transition-colors"></div>
            <div className="text-[10px] font-data text-sasta-accent mb-2 tracking-[0.2em]">ACCESS_KEY</div>
            <div className="flex items-baseline justify-between gap-2 mb-4">
              <span className="text-4xl font-zero font-bold text-white tracking-widest">{shortCode}</span>
            </div>
            <button
              onClick={handleCopyGameId}
              className="w-full bg-sasta-accent text-black py-2 font-bold font-data text-xs hover:bg-white transition-colors uppercase tracking-widest"
            >
              {copied ? '✓ KEY_COPIED' : 'COPY_ACCESS_KEY'}
            </button>
            <div className="mt-4 flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-[10px] font-data text-zinc-500">NET_STATUS: LIVE</span>
            </div>
          </div>
        )}

        <div className="font-data text-xs border-l-2 border-black pl-3 py-1">
          <div className="opacity-50 mb-1">CURRENT_MODE</div>
          <div className="font-bold">{settings.win_condition || 'SUDDEN_DEATH'}</div>
        </div>

        {!hasJoined ? (
          <div className="border-2 border-black p-4 mt-auto">
            <div className="text-xs font-data font-bold mb-3">&gt; AUTHENTICATE_OPERATOR</div>
            <div className="flex flex-col gap-3">
              <input
                type="text"
                value={playerName}
                onChange={(e) => setPlayerName(e.target.value)}
                placeholder="CODENAME"
                className="w-full bg-gray-100 border-b-2 border-black p-3 font-data text-sm focus:outline-none focus:bg-sasta-accent/20 uppercase"
                onKeyPress={(e) => {
                  if (e.key === 'Enter' && playerName.trim() && !isJoining) handleJoin()
                }}
              />
              <button
                onClick={handleJoin}
                disabled={isJoining || !playerName.trim()}
                className="w-full bg-black text-white p-3 font-data font-bold hover:bg-gray-900 transition-colors disabled:opacity-50"
              >
                {isJoining ? 'CONNECTING...' : 'INIT_CONNECTION'}
              </button>
            </div>
          </div>
        ) : (
          <div className="bg-black p-6 shrink-0 border-t-4 border-sasta-accent mt-auto">
            <div className="flex justify-between items-center mb-4 text-zinc-500 text-[10px] font-data">
              <span>LAUNCH_SEQUENCE</span>
              <span>{readyCount}/{totalPlayers} ARMED</span>
            </div>

            <LaunchKey
              isReady={myPlayer?.ready || false}
              isLoading={isToggling}
              onToggle={handleToggleReady}
              playerName={myPlayer?.name}
              playerColor={myPlayer?.color}
            />

            {allReady && (
              <div className="mt-3 text-center text-sasta-accent text-xs font-bold animate-pulse">
                ⚠ LAUNCH IMMINENT ⚠
              </div>
            )}
          </div>
        )}
      </div>

      <div className="lg:col-span-6 bg-gray-50/50 p-6 lg:p-8 flex flex-col relative overflow-hidden">
        <div className="flex justify-between items-end mb-6 border-b-2 border-black pb-4">
          <div>
            <h2 className="font-data font-bold text-xl">SQUADRON</h2>
            <div className="text-xs font-data opacity-50 mt-1">ACTIVE OPERATORS</div>
          </div>
          <div className="font-zero text-4xl font-bold opacity-20">
            {totalPlayers.toString().padStart(2, '0')}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto pr-2 space-y-3 scrollbar-hide">
          {myPlayer && (
            <div className="flex items-center gap-4 p-4 bg-white border-2 border-black shadow-[4px_4px_0px_0px_rgba(0,0,0,1)] hover:translate-x-1 transition-transform">
              <div
                className="w-12 h-12 border-2 border-black flex items-center justify-center font-data font-bold text-white text-xl shrink-0"
                style={{ backgroundColor: myPlayer.color }}
              >
                {myPlayer.name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <div className="font-zero font-bold text-lg leading-none truncate">
                    {myPlayer.name?.toUpperCase()}
                  </div>
                  {isHost && <span className="text-[10px] bg-black text-sasta-accent px-1">CMD</span>}
                  <span className="text-[10px] border border-black px-1">YOU</span>
                </div>
                <div className={`text-xs font-data mt-1 ${myPlayer.ready ? 'text-green-600 font-bold' : 'text-orange-600'}`}>
                  {myPlayer.ready ? '● READY_FOR_DEPLOY' : '○ STANDBY'}
                </div>
              </div>
            </div>
          )}

          {otherPlayers.map((p) => (
            <div key={p.id} className="flex items-center gap-4 p-4 bg-white border border-gray-300 hover:border-black transition-colors group">
              <div
                className="w-12 h-12 border-2 border-black flex items-center justify-center font-data font-bold text-white text-xl shrink-0 grayscale opacity-80"
                style={{ backgroundColor: p.color }}
              >
                {p.name?.charAt(0)?.toUpperCase()}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <div className="font-zero font-bold text-lg leading-none truncate text-gray-700">
                    {p.name?.toUpperCase()}
                  </div>
                  {p.id === game?.host_id && <span className="text-[10px] bg-gray-200 px-1">CMD</span>}
                </div>
                <div className={`text-xs font-data mt-1 ${p.ready ? 'text-green-600 font-bold' : 'text-gray-400'}`}>
                  {p.ready ? '● READY' : '○ STANDBY'}
                </div>
              </div>
              {isHost && (
                <button
                  onClick={() => handleKickPlayer(p.id)}
                  className="text-xs font-data text-red-500 hover:bg-red-50 px-3 py-2 border border-transparent hover:border-red-500 transition-all"
                >
                  EJECT
                </button>
              )}
            </div>
          ))}

          {totalPlayers === 0 && (
            <div className="h-full flex flex-col items-center justify-center opacity-30">
              <div className="text-6xl mb-4">📡</div>
              <div className="font-data font-bold">SEARCHING_FOR_SIGNALS...</div>
            </div>
          )}
        </div>
      </div>

      <div className="lg:col-span-3 bg-white flex flex-col h-full overflow-hidden border-l border-black">
        <div className="flex-1 overflow-y-auto p-6 pb-8">
          <h3 className="font-data font-bold text-sm mb-6 border-b-2 border-black pb-2">MISSION_PARAMETERS</h3>
          {hasJoined ? (
            <GameSettingsPanel
              settings={settings}
              onUpdate={handleUpdateSettings}
              onSave={handleSaveSettings}
              hasChanges={hasChanges}
              isHost={isHost}
              alwaysExpanded={true}
            />
          ) : (
            <div className="text-xs text-gray-400 font-data p-4 border border-dashed border-gray-300 text-center">
              ACCESS DISTRIBUTED AFTER AUTHENTICATION
            </div>
          )}
        </div>


      </div>

      <RulesModal isOpen={showRules} onClose={() => setShowRules(false)} />
    </div>
  )
}
