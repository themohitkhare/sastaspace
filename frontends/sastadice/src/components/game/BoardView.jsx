import { useState, useEffect, useRef } from 'react'
import TileComponent from './TileComponent'
import PlayerToken from './PlayerToken'

const DEFAULT_TILE_SIZE = 72
const MIN_TILE_SIZE = 50
const MAX_TILE_SIZE = 150

function useTileSize(boardSize, containerRef) {
  const [tileSize, setTileSize] = useState(DEFAULT_TILE_SIZE)

  useEffect(() => {
    function calculateTileSize() {
      if (!containerRef.current) return
      
      const container = containerRef.current
      const availableWidth = container.clientWidth - 16
      const availableHeight = container.clientHeight - 16
      
      const sizeFromWidth = Math.floor(availableWidth / boardSize)
      const sizeFromHeight = Math.floor(availableHeight / boardSize)
      
      const calculated = Math.min(sizeFromWidth, sizeFromHeight)
      const clamped = Math.max(MIN_TILE_SIZE, Math.min(MAX_TILE_SIZE, calculated))
      
      setTileSize(clamped)
    }

    calculateTileSize()
    window.addEventListener('resize', calculateTileSize)
    
    const resizeObserver = new ResizeObserver(calculateTileSize)
    if (containerRef.current) {
      resizeObserver.observe(containerRef.current)
    }
    
    return () => {
      window.removeEventListener('resize', calculateTileSize)
      resizeObserver.disconnect()
    }
  }, [boardSize, containerRef])

  return tileSize
}

export default function BoardView({ tiles = [], boardSize, players = [], children }) {
  const containerRef = useRef(null)
  const tileSize = useTileSize(boardSize, containerRef)

  if (!boardSize || boardSize < 2) {
    return <div className="text-center p-8 font-zero">LOADING BOARD...</div>
  }

  const isOnPerimeter = (x, y) => x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1

  return (
    <div ref={containerRef} className="board-wrapper w-full h-full flex justify-center items-center p-2">
      <div
        className="board-container relative border-brutal"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${boardSize}, ${tileSize}px)`,
          gridTemplateRows: `repeat(${boardSize}, ${tileSize}px)`,
          gap: '0px',
          backgroundColor: '#000',
        }}
      >
        {tiles.map((tile) => {
          if (!isOnPerimeter(tile.x, tile.y)) return null
          return (
            <div key={tile.id} style={{ gridColumn: tile.x + 1, gridRow: tile.y + 1 }}>
              <TileComponent tile={tile} players={players} size={tileSize} />
            </div>
          )
        })}

        {players.map((player) => {
          const tile = tiles.find((t) => t.position === player.position)
          if (!tile || !isOnPerimeter(tile.x, tile.y)) return null

          const playersOnSameTile = players.filter(p => p.position === player.position)
          const playerIndex = playersOnSameTile.findIndex(p => p.id === player.id)
          const tokenOffset = Math.floor(tileSize / 4)

          return (
            <PlayerToken
              key={player.id}
              player={player}
              tile={tile}
              boardSize={boardSize}
              tileSize={tileSize}
              offsetX={(playerIndex % 2) * tokenOffset - tokenOffset / 2}
              offsetY={Math.floor(playerIndex / 2) * tokenOffset - tokenOffset / 2}
            />
          )
        })}

        {boardSize > 2 && (
          <div
            className="board-center bg-sasta-white border-brutal flex flex-col items-center justify-center p-2 overflow-hidden"
            style={{ gridColumn: `2 / ${boardSize}`, gridRow: `2 / ${boardSize}` }}
          >
            {children}
          </div>
        )}
      </div>
    </div>
  )
}

export { DEFAULT_TILE_SIZE as TILE_SIZE }
