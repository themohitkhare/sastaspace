/**
 * IsometricContainer - Handles CSS transform for isometric board view
 */
import React from 'react'

const TILE_SIZE = 100 // pixels

export default function IsometricContainer({ children, boardSize }) {
  return (
    <div
      className="isometric-board relative"
      style={{
        transform: 'rotateX(60deg) rotateZ(-45deg)',
        transformStyle: 'preserve-3d',
        width: `${boardSize * TILE_SIZE}px`,
        height: `${boardSize * TILE_SIZE}px`,
        margin: '0 auto',
        perspective: '1000px',
      }}
    >
      {children}
    </div>
  )
}

export { TILE_SIZE }
