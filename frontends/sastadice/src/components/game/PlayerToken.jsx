/**
 * PlayerToken - Renders player avatar/token on the board
 */
import React from 'react'
import { TILE_SIZE } from './IsometricContainer'

export default function PlayerToken({ player, position, boardSize, board }) {
  // Find tile at player's position
  const tile = board?.find((t) => t.position === position)

  if (!tile) {
    return null
  }

  const isOnPerimeter = isOnBoardPerimeter(tile.x, tile.y, boardSize)
  if (!isOnPerimeter) {
    return null
  }

  return (
    <div
      className="player-token absolute bg-sasta-black text-sasta-white rounded-full border-2 border-sasta-white"
      style={{
        left: `${tile.x * TILE_SIZE + TILE_SIZE / 2 - 15}px`,
        top: `${tile.y * TILE_SIZE + TILE_SIZE / 2 - 15}px`,
        width: '30px',
        height: '30px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '12px',
        fontWeight: 'bold',
        zIndex: 10,
      }}
      title={player.name}
    >
      {player.name.charAt(0).toUpperCase()}
    </div>
  )
}

function isOnBoardPerimeter(x, y, boardSize) {
  return x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1
}
