/**
 * TileComponent - Renders a single game tile with isometric positioning
 */
import React from 'react'
import { TILE_SIZE } from './IsometricContainer'

export default function TileComponent({ tile, boardSize, style = {} }) {
  const isOnPerimeter = isOnBoardPerimeter(tile.x, tile.y, boardSize)

  if (!isOnPerimeter) {
    return null // Don't render inner tiles
  }

  const tileTypeColors = {
    PROPERTY: 'bg-blue-500',
    TAX: 'bg-red-500',
    CHANCE: 'bg-yellow-500',
    TRAP: 'bg-purple-500',
    BUFF: 'bg-green-500',
    NEUTRAL: 'bg-gray-300',
  }

  const colorClass = tileTypeColors[tile.type] || 'bg-gray-300'

  return (
    <div
      className={`tile ${colorClass} border-brutal-sm shadow-brutal-sm`}
      style={{
        position: 'absolute',
        left: `${tile.x * TILE_SIZE}px`,
        top: `${tile.y * TILE_SIZE}px`,
        width: `${TILE_SIZE}px`,
        height: `${TILE_SIZE}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: '12px',
        fontWeight: 'bold',
        textAlign: 'center',
        ...style,
      }}
    >
      <div className="p-2">
        <div className="text-xs">{tile.name}</div>
        {tile.owner_id && (
          <div className="text-xs mt-1">Owner: {tile.owner_id.slice(0, 4)}</div>
        )}
      </div>
    </div>
  )
}

function isOnBoardPerimeter(x, y, boardSize) {
  return x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1
}
