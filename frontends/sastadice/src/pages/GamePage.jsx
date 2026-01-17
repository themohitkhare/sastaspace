import { useCallback } from 'react'
import { useSastaPolling } from '../hooks/useSastaPolling'
import { useGameStore } from '../store/useGameStore'
import BoardView from '../components/game/BoardView'
import PlayerPanel from '../components/game/PlayerPanel'
import ActionPanel from '../components/game/ActionPanel'
import DiceDisplay from '../components/game/DiceDisplay'

export default function GamePage() {
  const gameId = useGameStore((s) => s.gameId)
  const playerId = useGameStore((s) => s.playerId)
  const game = useGameStore((s) => s.game)
  const isMyTurn = useGameStore((s) => s.isMyTurn)()

  const { refetch } = useSastaPolling(gameId, 1500)
  const handleActionComplete = useCallback(() => refetch(), [refetch])

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

  const currentPlayer = game.players?.find((p) => p.id === game.current_turn_player_id)
  const myPlayer = game.players?.find((p) => p.id === playerId)

  return (
    <div className="min-h-screen bg-sasta-white">
      <header className="border-b-4 border-sasta-black bg-sasta-white">
        <div className="max-w-7xl mx-auto px-4 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-3xl font-bold font-zero">SASTADICE</h1>
            <p className="text-sm font-zero opacity-60">GAME: {gameId?.slice(0, 8)}...</p>
          </div>
          
          <div className={`border-brutal-sm px-4 py-2 ${isMyTurn ? 'bg-sasta-accent' : 'bg-sasta-white'}`}>
            <div className="text-xs font-zero font-bold opacity-60">CURRENT TURN</div>
            <div className="font-zero font-bold">{currentPlayer?.name?.toUpperCase() || 'N/A'}</div>
            {isMyTurn && <div className="text-xs font-zero text-sasta-black font-bold">YOUR TURN!</div>}
          </div>

          {myPlayer && (
            <div className="text-right border-brutal-sm bg-sasta-black text-sasta-accent px-4 py-2">
              <div className="text-xs font-zero opacity-60">YOUR CASH</div>
              <div className="text-2xl font-zero font-bold">${myPlayer.cash.toLocaleString()}</div>
            </div>
          )}
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-4 flex gap-4">
        <div className="flex-1 border-brutal-lg bg-sasta-white shadow-brutal-lg overflow-hidden">
          <BoardView
            tiles={game.board || []}
            boardSize={game.board_size || 0}
            players={game.players || []}
          >
            <div className="flex flex-col items-center gap-4 w-full max-w-xs p-4">
              <DiceDisplay lastDiceRoll={game.last_dice_roll} />
              <ActionPanel
                gameId={gameId}
                playerId={playerId}
                turnPhase={game.turn_phase}
                pendingDecision={game.pending_decision}
                isMyTurn={isMyTurn}
                lastEventMessage={game.last_event_message}
                onActionComplete={handleActionComplete}
              />
            </div>
          </BoardView>
        </div>

        <div className="w-72 border-brutal-lg bg-sasta-white shadow-brutal-lg p-4">
          <PlayerPanel
            players={game.players || []}
            currentTurnPlayerId={game.current_turn_player_id}
            currentPlayerId={playerId}
            tiles={game.board || []}
          />

          <div className="mt-4 pt-4 border-t-2 border-sasta-black">
            <h4 className="text-xs font-zero font-bold mb-3">GAME INFO</h4>
            <div className="space-y-2 text-sm font-zero">
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
    </div>
  )
}
