import { useState, useEffect, useRef } from 'react'
import TileComponent from './TileComponent'
import PlayerToken from './PlayerToken'

export default function BoardView({ tiles = [], boardSize, players = [], children }) {
  const containerRef = useRef(null)
  const wrapperRef = useRef(null)
  // We track dimensions only for text scaling & token positioning
  // The Layout itself is now handled purely by CSS
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [boardSizePx, setBoardSizePx] = useState(0)

  // Calculate board size based on available container space
  useEffect(() => {
    if (!wrapperRef.current) return

    const calculateSize = () => {
      const wrapper = wrapperRef.current
      if (!wrapper) return

      // Use requestAnimationFrame to ensure layout is complete
      requestAnimationFrame(() => {
        const rect = wrapper.getBoundingClientRect()
        const availableWidth = Math.max(0, rect.width - 32) // Subtract padding (p-4 = 16px * 2)
        const availableHeight = Math.max(0, rect.height - 32) // Subtract padding
        
        // Use the smaller dimension to ensure square fits
        const size = Math.min(availableWidth, availableHeight)
        setBoardSizePx(size)
      })
    }

    // Initial calculation with a small delay to ensure layout is ready
    const timeoutId = setTimeout(calculateSize, 0)

    // Recalculate on resize and orientation change
    const resizeObserver = new ResizeObserver(calculateSize)
    resizeObserver.observe(wrapperRef.current)

    // Also listen to orientation changes
    const handleOrientationChange = () => {
      // Wait for orientation change to complete, then recalculate multiple times
      setTimeout(calculateSize, 50)
      setTimeout(calculateSize, 200)
      setTimeout(calculateSize, 500)
    }
    window.addEventListener('orientationchange', handleOrientationChange)
    window.addEventListener('resize', calculateSize)

    return () => {
      clearTimeout(timeoutId)
      resizeObserver.disconnect()
      window.removeEventListener('orientationchange', handleOrientationChange)
      window.removeEventListener('resize', calculateSize)
    }
  }, [])

  useEffect(() => {
    if (!containerRef.current) return

    const observer = new ResizeObserver(([entry]) => {
      // Just measure what CSS created
      if (entry?.contentRect) {
        setDimensions({
          width: entry.contentRect.width,
          height: entry.contentRect.height
        })
      }
    })

    observer.observe(containerRef.current)
    return () => observer.disconnect()
  }, [])

  // Calculate dynamic scale for props that need it (like PlayerToken)
  // But we default to 0 to prevent "NaN" errors during first render
  const tileSize = dimensions.width > 0 ? dimensions.width / boardSize : 0
  
  if (!boardSize || boardSize < 2) {
    return <div className="text-center p-8 font-zero animate-pulse">LOADING BOARD...</div>
  }

  const isOnPerimeter = (x, y) => x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1

  return (
    // overflow-hidden on the wrapper is the final safety net
    <div 
      ref={wrapperRef}
      className="board-wrapper w-full h-full flex justify-center items-center p-4 overflow-hidden"
      style={{ overflow: 'hidden' }}
    >
      <div
        ref={containerRef}
        className="board-container relative border-brutal bg-black grid"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${boardSize}, 1fr)`,
          gridTemplateRows: `repeat(${boardSize}, 1fr)`,
          gap: '0px',
          
          // STRICT SIZING:
          // Use calculated size based on available container space
          // This ensures the board fits perfectly without scrollbars
          width: boardSizePx > 0 ? `${boardSizePx}px` : '100%',
          height: boardSizePx > 0 ? `${boardSizePx}px` : '100%',
          maxWidth: '100%',
          maxHeight: '100%',
          aspectRatio: boardSizePx > 0 ? 'unset' : '1 / 1', // Only use aspect-ratio as fallback
          
          flexShrink: 0, // Prevent flexbox from squishing it
        }}
      >
        {/* Render Tiles */}
        {tiles.map((tile) => {
          if (!isOnPerimeter(tile.x, tile.y)) return null
          return (
            <div 
              key={tile.id} 
              style={{ 
                gridColumn: tile.x + 1, 
                gridRow: tile.y + 1,
              }}
              className="w-full h-full relative overflow-hidden"
            >
              <TileComponent 
                tile={tile} 
                players={players} 
                size={tileSize} // Pass dynamic size for internal styling
              />
            </div>
          )
        })}

        {/* Render Player Tokens (Overlay) */}
        {players.map((player) => {
          const tile = tiles.find((t) => t.position === player.position)
          if (!tile || !isOnPerimeter(tile.x, tile.y)) return null

          // Logic to stack players nicely
          const playersOnSameTile = players.filter(p => p.position === player.position)
          const playerIndex = playersOnSameTile.findIndex(p => p.id === player.id)
          
          // Calculate token spacing based on real tile size
          const tokenOffset = Math.floor(tileSize / 4)
          
          return (
            <div
              key={player.id}
              style={{
                gridColumn: tile.x + 1,
                gridRow: tile.y + 1,
                pointerEvents: 'none', // Let clicks pass through to tile
                zIndex: 20
              }}
              className="relative w-full h-full"
            >
               {/* Wrapper to center the token logic */}
               <PlayerToken
                  player={player}
                  tile={tile}
                  boardSize={boardSize}
                  tileSize={tileSize}
                  // Recalculate offsets dynamically
                  offsetX={(playerIndex % 2) * tokenOffset - tokenOffset / 2}
                  offsetY={Math.floor(playerIndex / 2) * tokenOffset - tokenOffset / 2}
                />
            </div>
          )
        })}

        {/* Center Content (The Void) */}
        {boardSize > 2 && (
          <div
            className="board-center bg-sasta-white border-brutal flex flex-col items-center justify-center p-2 overflow-hidden z-10"
            style={{ 
              gridColumn: `2 / ${boardSize}`, 
              gridRow: `2 / ${boardSize}` 
            }}
          >
            {children}
          </div>
        )}
      </div>
    </div>
  )
}
