/**
 * PlayerToken - Renders player avatar/token on the board (Brutalist style)
 */
import React from 'react'

const TILE_SIZE = 72

export default function PlayerToken({ 
  player, 
  tile, 
  boardSize, 
  offsetX = 0, 
  offsetY = 0 
}) {
  if (!tile) {
    return null
  }

  const isOnPerimeter = isOnBoardPerimeter(tile.x, tile.y, boardSize)
  if (!isOnPerimeter) {
    return null
  }

  // Player color with fallback
  const playerColor = player.color || '#000000'

  return (
    <div
      className="player-token absolute font-zero font-bold text-sasta-white"
      style={{
        // Position relative to grid
        gridColumn: tile.x + 1,
        gridRow: tile.y + 1,
        // Center in tile with offset for multiple players
        transform: `translate(${TILE_SIZE / 2 - 12 + offsetX}px, ${TILE_SIZE / 2 - 12 + offsetY}px)`,
        backgroundColor: playerColor,
        width: '24px',
        height: '24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '10px',
        border: '2px solid #000',
        zIndex: 20,
        pointerEvents: 'none',
      }}
      title={`${player.name} - $${player.cash}`}
    >
      {player.name.charAt(0).toUpperCase()}
    </div>
  )
}

function isOnBoardPerimeter(x, y, boardSize) {
  return x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1
}

export { TILE_SIZE }
