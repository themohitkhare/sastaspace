/**
 * GamePage - Main game view with isometric board
 */
import React from 'react'
import { useSastaPolling } from '../hooks/useSastaPolling'
import { useGameStore } from '../store/useGameStore'
import IsometricContainer from '../components/game/IsometricContainer'
import TileComponent from '../components/game/TileComponent'
import PlayerToken from '../components/game/PlayerToken'
import DiceRoller from '../components/game/DiceRoller'

export default function GamePage() {
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)

  // Start polling for game state updates
  useSastaPolling(gameId, 2000)

  if (!game) {
    return (
      <div className="min-h-screen bg-sasta-white p-8">
        <p className="font-zero">Loading game...</p>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-sasta-white p-8">
      <h1 className="text-4xl font-bold font-zero mb-6">SASTADICE GAME</h1>

      <div className="mb-8 border-brutal-lg bg-sasta-white p-4 shadow-brutal-lg">
        <p className="font-zero">
          Status: <span className="font-bold">{game.status}</span>
        </p>
        <p className="font-zero">
          Turn: <span className="font-bold">
            {game.players?.find((p) => p.id === game.current_turn_player_id)?.name || 'N/A'}
          </span>
        </p>
      </div>

      <IsometricContainer boardSize={game.board_size || 0}>
        {game.board?.map((tile) => (
          <TileComponent
            key={tile.id}
            tile={tile}
            boardSize={game.board_size}
          />
        ))}

        {game.players?.map((player) => (
          <PlayerToken
            key={player.id}
            player={player}
            position={player.position}
            boardSize={game.board_size}
            board={game.board}
          />
        ))}
      </IsometricContainer>

      <div className="mt-8">
        <DiceRoller />
      </div>
    </div>
  )
}
