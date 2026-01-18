import { useCallback, useEffect, useRef, useState } from 'react'
import { useSastaPolling } from '../hooks/useSastaPolling'
import { useGameStore } from '../store/useGameStore'
import { apiClient } from '../api/apiClient'
import BoardView from '../components/game/BoardView'
import PlayerPanel from '../components/game/PlayerPanel'
import VictoryScreen from '../components/game/VictoryScreen'
import TurnAnnouncement from '../components/game/TurnAnnouncement'
import CenterStage from '../components/game/CenterStage'
import AuctionModal from '../components/game/AuctionModal'
import PropertyDetailsModal from '../components/game/PropertyDetailsModal'

const CPU_NAMES = new Set(['ROBOCOP', 'CHAD BOT', 'KAREN.EXE', 'STONKS', 'CPU-1', 'CPU-2', 'CPU-3', 'CPU-4', 'CPU-5'])

export default function GamePage() {
  const gameId = useGameStore((s) => s.gameId)
  const playerId = useGameStore((s) => s.playerId)
  const game = useGameStore((s) => s.game)
  const isMyTurn = useGameStore((s) => s.isMyTurn)()
  const cpuActionRef = useRef(false)
  const lastCpuPlayerIdRef = useRef(null)
  const [showTurnAnnouncement, setShowTurnAnnouncement] = useState(false)
  const [announcedPlayer, setAnnouncedPlayer] = useState(null)
  const lastAnnouncedTurnRef = useRef(null)

  // Property Details
  const [selectedTile, setSelectedTile] = useState(null)

  const pollingInterval = game?.turn_phase === 'AUCTION' ? 300 : 1500
  const { refetch } = useSastaPolling(gameId, pollingInterval)
  const handleActionComplete = useCallback(async () => {
    await refetch()
  }, [refetch])

  const currentPlayer = game?.players?.find((p) => p.id === game?.current_turn_player_id)
  const isCpuTurn = currentPlayer && CPU_NAMES.has(currentPlayer.name) && game?.status === 'ACTIVE'
  const currentTurnPlayerId = game?.current_turn_player_id
  const turnPhase = game?.turn_phase

  useEffect(() => {
    if (currentPlayer && currentTurnPlayerId !== lastAnnouncedTurnRef.current && game?.status === 'ACTIVE') {
      lastAnnouncedTurnRef.current = currentTurnPlayerId
      setAnnouncedPlayer(currentPlayer)
      setShowTurnAnnouncement(true)
      const timeout = setTimeout(() => setShowTurnAnnouncement(false), 1600)
      return () => clearTimeout(timeout)
    }
  }, [currentTurnPlayerId, currentPlayer, game?.status])

  useEffect(() => {
    if (currentTurnPlayerId && lastCpuPlayerIdRef.current && lastCpuPlayerIdRef.current !== currentTurnPlayerId) {
      cpuActionRef.current = false
    }
    if (currentTurnPlayerId) {
      lastCpuPlayerIdRef.current = currentTurnPlayerId
    }
  }, [currentTurnPlayerId])

  const handleBid = async (amount) => {
    try {
      await apiClient.post(`/sastadice/games/${gameId}/action`, {
        type: 'BID',
        player_id: playerId,
        payload: { amount }
      })
      refetch()
    } catch (err) {
      console.error('Bid failed:', err)
    }
  }

  const handleAuctionExpire = async () => {
    try {
      await apiClient.post(`/sastadice/games/${gameId}/action`, {
        type: 'RESOLVE_AUCTION',
        player_id: playerId,
        payload: {}
      })
      refetch()
    } catch (err) {
      console.error('Resolve failed:', err)
    }
  }

  useEffect(() => {
    if (!isCpuTurn || cpuActionRef.current || !gameId) return

    const processCpuTurns = async () => {
      // ... same content ...
      cpuActionRef.current = true
      await new Promise(r => setTimeout(r, 600))

      try {
        await apiClient.post(`/sastadice/games/${gameId}/cpu-turn`)
        await refetch()
        await new Promise(r => setTimeout(r, 200))
        await refetch()
      } catch (error) {
        await refetch()
      } finally {
        setTimeout(() => {
          cpuActionRef.current = false
        }, 800)
      }
    }

    processCpuTurns()
  }, [isCpuTurn, gameId, currentTurnPlayerId, turnPhase, refetch])

  const myPlayer = game?.players?.find((p) => p.id === playerId)

  const currentTile = currentPlayer && game?.board
    ? game.board[currentPlayer.position] || null
    : null
  const tileOwner = currentTile?.owner_id
    ? game?.players?.find(p => p.id === currentTile.owner_id)
    : null

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

  if (game.status === 'FINISHED') {
    return <VictoryScreen game={game} />
  }

  return (
    <div className="h-screen bg-sasta-white flex flex-col overflow-hidden">
      <header className="border-b-2 border-sasta-black bg-sasta-white shrink-0">
        <div className="max-w-7xl mx-auto px-2 py-1 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <h1 className="text-lg sm:text-xl font-bold font-zero">SASTADICE</h1>
            <span className="text-[10px] font-data opacity-40 hidden sm:inline">#{gameId?.slice(0, 8)}</span>
          </div>

          <div className={`border-brutal-sm px-2 py-1 ${isMyTurn ? 'bg-sasta-accent' : 'bg-sasta-white'}`}>
            <div className="flex items-center gap-2">
              <span className="font-data font-bold text-xs">{currentPlayer?.name?.toUpperCase() || 'N/A'}</span>
              {isMyTurn && <span className="text-[10px] font-data bg-sasta-black text-sasta-accent px-1">YOUR TURN</span>}
              {isCpuTurn && <span className="text-[10px] font-data text-blue-600 animate-pulse">THINKING...</span>}
              {!playerId && <span className="text-[10px] font-data text-blue-600">👁️ SPECTATOR</span>}
            </div>
          </div>
        </div>
      </header>

      <div className="flex-1 min-h-0 max-w-full mx-auto w-full p-1 sm:p-2 flex flex-col lg:flex-row gap-2 overflow-hidden">
        <div
          className="flex-1 min-h-0 min-w-0 border-brutal-sm bg-sasta-white shadow-brutal-sm overflow-hidden order-1"
          style={{ display: 'flex', flexDirection: 'column', position: 'relative' }}
        >
          <BoardView
            tiles={game.board || []}
            boardSize={game.board_size || 0}
            players={game.players || []}
            onTileClick={setSelectedTile}
          >
            <CenterStage
              lastDiceRoll={game.last_dice_roll}
              gameId={gameId}
              playerId={playerId}
              turnPhase={game.turn_phase}
              pendingDecision={game.pending_decision}
              isMyTurn={isMyTurn}
              isCpuTurn={isCpuTurn}
              currentPlayer={currentPlayer}
              currentTile={currentTile}
              tileOwner={tileOwner}
              myPlayerCash={myPlayer?.cash}
              lastEventMessage={game.last_event_message}
              onActionComplete={handleActionComplete}
            />
          </BoardView>
        </div>

        <div className="w-full lg:w-56 lg:shrink-0 border-brutal-sm bg-sasta-white shadow-brutal-sm p-2 order-2 lg:max-h-full lg:overflow-auto">
          <PlayerPanel
            players={game.players || []}
            currentTurnPlayerId={game.current_turn_player_id}
            currentPlayerId={playerId}
            tiles={game.board || []}
          />

          <div className="mt-3 pt-3 border-t-2 border-sasta-black">
            <h4 className="text-xs font-data font-bold mb-2">GAME INFO</h4>
            <div className="grid grid-cols-2 lg:grid-cols-1 gap-1 text-xs font-data">
              <div className="flex justify-between border-brutal-sm p-1">
                <span className="opacity-60">STATUS:</span>
                <span className="font-bold">{game.status}</span>
              </div>
              <div className="flex justify-between border-brutal-sm p-1">
                <span className="opacity-60">PHASE:</span>
                <span className="font-bold">{game.turn_phase}</span>
              </div>
              <div className="flex justify-between border-brutal-sm p-1 bg-sasta-accent">
                <span>GO BONUS:</span>
                <span className="font-bold">${game.go_bonus}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <TurnAnnouncement
        playerName={announcedPlayer?.name}
        isMyTurn={announcedPlayer?.id === playerId}
        show={showTurnAnnouncement}
      />

      {game.turn_phase === 'AUCTION' && game.auction_state && (
        <AuctionModal
          auctionState={game.auction_state}
          tiles={game.board}
          players={game.players}
          playerId={playerId}
          onBid={handleBid}
          onExpire={handleAuctionExpire}
        />
      )}

      <PropertyDetailsModal
        tile={selectedTile}
        onClose={() => setSelectedTile(null)}
        onRefresh={refetch}
      />
    </div>
  )
}
