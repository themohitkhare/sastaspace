import { useCallback, useEffect, useRef } from 'react'
import { useSastaPolling } from '../hooks/useSastaPolling'
import { useGameStore } from '../store/useGameStore'
import { apiClient } from '../api/apiClient'
import BoardView from '../components/game/BoardView'
import PlayerPanel from '../components/game/PlayerPanel'
import ActionPanel from '../components/game/ActionPanel'
import DiceDisplay from '../components/game/DiceDisplay'

const CPU_NAMES = new Set(['ROBOCOP', 'CHAD BOT', 'KAREN.EXE', 'STONKS', 'CPU-1', 'CPU-2', 'CPU-3', 'CPU-4', 'CPU-5'])

export default function GamePage() {
  const gameId = useGameStore((s) => s.gameId)
  const playerId = useGameStore((s) => s.playerId)
  const game = useGameStore((s) => s.game)
  const isMyTurn = useGameStore((s) => s.isMyTurn)()
  const cpuActionRef = useRef(false)
  const lastCpuPlayerIdRef = useRef(null)

  const { refetch } = useSastaPolling(gameId, 1500)
  const handleActionComplete = useCallback(async () => {
    await refetch()
  }, [refetch])

  const currentPlayer = game?.players?.find((p) => p.id === game?.current_turn_player_id)
  const isCpuTurn = currentPlayer && CPU_NAMES.has(currentPlayer.name) && game?.status === 'ACTIVE'
  const currentTurnPlayerId = game?.current_turn_player_id
  const turnPhase = game?.turn_phase

  // Reset CPU action ref if the current player changes (turn advanced)
  useEffect(() => {
    if (currentTurnPlayerId && lastCpuPlayerIdRef.current && lastCpuPlayerIdRef.current !== currentTurnPlayerId) {
      // Player changed, reset the processing flag to allow next CPU turn
      cpuActionRef.current = false
    }
    if (currentTurnPlayerId) {
      lastCpuPlayerIdRef.current = currentTurnPlayerId
    }
  }, [currentTurnPlayerId])

  useEffect(() => {
    if (!isCpuTurn || cpuActionRef.current || !gameId) return

    const processCpuTurns = async () => {
      cpuActionRef.current = true
      
      // Small delay to show "CPU THINKING..." message
      await new Promise(r => setTimeout(r, 600))
      
      try {
        await apiClient.post(`/sastadice/games/${gameId}/cpu-turn`)
        // Immediately refresh game state after CPU turn
        await refetch()
        
        // Additional refresh after a short delay to catch any state updates
        await new Promise(r => setTimeout(r, 200))
        await refetch()
      } catch (error) {
        console.error('CPU turn error:', error)
        // Still refetch to get updated state even on error
        await refetch()
      } finally {
        // Reset the ref after state has had time to update
        // Use a longer delay to ensure polling has a chance to update
        setTimeout(() => {
          cpuActionRef.current = false
        }, 800)
      }
    }

    processCpuTurns()
  }, [isCpuTurn, gameId, currentTurnPlayerId, turnPhase, refetch])

  const myPlayer = game?.players?.find((p) => p.id === playerId)

  if (!game) {
    return (
      <div className="min-h-screen bg-sasta-white flex items-center justify-center">
        <div className="text-center border-brutal-lg p-8 shadow-brutal-lg">
          <div className="font-zero text-2xl mb-4">LOADING...</div>
          <div className="w-8 h-8 border-4 border-sasta-black border-t-sasta-accent animate-spin mx-auto"></div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen bg-sasta-white flex flex-col overflow-hidden">
      <header className="border-b-4 border-sasta-black bg-sasta-white shrink-0">
        <div className="max-w-7xl mx-auto px-2 sm:px-4 py-2 sm:py-4 flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <h1 className="text-xl sm:text-3xl font-bold font-zero truncate">SASTADICE</h1>
            <p className="text-xs sm:text-sm font-zero opacity-60 truncate">GAME: {gameId?.slice(0, 8)}...</p>
          </div>
          
          <div className={`border-brutal-sm px-2 sm:px-4 py-1 sm:py-2 ${isMyTurn ? 'bg-sasta-accent' : 'bg-sasta-white'}`}>
            <div className="text-[10px] sm:text-xs font-zero font-bold opacity-60">CURRENT TURN</div>
            <div className="font-zero font-bold text-sm sm:text-base">{currentPlayer?.name?.toUpperCase() || 'N/A'}</div>
            {isMyTurn && <div className="text-[10px] sm:text-xs font-zero text-sasta-black font-bold">YOUR TURN!</div>}
            {isCpuTurn && <div className="text-[10px] sm:text-xs font-zero text-blue-600 font-bold animate-pulse">CPU THINKING...</div>}
            {!playerId && <div className="text-[10px] sm:text-xs font-zero text-blue-600 font-bold">👁️ SPECTATOR</div>}
          </div>

          {myPlayer && (
            <div className="text-right border-brutal-sm bg-sasta-black text-sasta-accent px-2 sm:px-4 py-1 sm:py-2">
              <div className="text-[10px] sm:text-xs font-zero opacity-60">YOUR CASH</div>
              <div className="text-lg sm:text-2xl font-zero font-bold">${myPlayer.cash.toLocaleString()}</div>
            </div>
          )}
        </div>
      </header>

      <div className="flex-1 min-h-0 max-w-full mx-auto w-full p-2 sm:p-4 flex flex-col lg:flex-row gap-4 overflow-hidden">
        <div 
          className="flex-1 min-h-0 min-w-0 border-brutal-lg bg-sasta-white shadow-brutal-lg overflow-hidden order-1 lg:order-1"
          style={{
            display: 'flex',
            flexDirection: 'column',
            position: 'relative',
          }}
        >
          <BoardView
            tiles={game.board || []}
            boardSize={game.board_size || 0}
            players={game.players || []}
          >
            <DiceDisplay lastDiceRoll={game.last_dice_roll} />
            {game.last_event_message && (
              <p className="font-zero text-xs sm:text-sm text-center mt-2 p-2 bg-sasta-accent/20 border border-sasta-black">
                {game.last_event_message}
              </p>
            )}
          </BoardView>
        </div>

        <div className="w-full lg:w-64 lg:shrink-0 border-brutal-lg bg-sasta-white shadow-brutal-lg p-3 sm:p-4 order-2 lg:order-2 lg:max-h-full lg:overflow-auto">
          <PlayerPanel
            players={game.players || []}
            currentTurnPlayerId={game.current_turn_player_id}
            currentPlayerId={playerId}
            tiles={game.board || []}
          />

          <div className="mt-3 sm:mt-4 pt-3 sm:pt-4 border-t-2 border-sasta-black">
            <h4 className="text-xs font-zero font-bold mb-2 sm:mb-3">GAME INFO</h4>
            <div className="grid grid-cols-2 lg:grid-cols-1 gap-2 text-xs sm:text-sm font-zero">
              <div className="flex justify-between border-brutal-sm p-2">
                <span className="opacity-60">STATUS:</span>
                <span className="font-bold">{game.status}</span>
              </div>
              <div className="flex justify-between border-brutal-sm p-2">
                <span className="opacity-60">PHASE:</span>
                <span className="font-bold">{game.turn_phase}</span>
              </div>
              <div className="flex justify-between border-brutal-sm p-2">
                <span className="opacity-60">BOARD:</span>
                <span className="font-bold">{game.board_size}x{game.board_size}</span>
              </div>
              <div className="flex justify-between border-brutal-sm p-2 bg-sasta-accent">
                <span>GO BONUS:</span>
                <span className="font-bold">${game.go_bonus}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Always render ActionPanel container to prevent layout shifts */}
      <div className="shrink-0 border-t-4 border-sasta-black bg-sasta-white p-2 sm:p-4">
        <div className="max-w-md mx-auto">
          <ActionPanel
            gameId={gameId}
            playerId={playerId}
            turnPhase={game.turn_phase}
            pendingDecision={game.pending_decision}
            isMyTurn={isMyTurn}
            lastEventMessage={null}
            onActionComplete={handleActionComplete}
          />
        </div>
      </div>
    </div>
  )
}
