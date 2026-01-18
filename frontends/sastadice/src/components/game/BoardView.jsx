import { useState, useEffect, useRef } from 'react'
import TileComponent from './TileComponent'
import PlayerToken from './PlayerToken'

export default function BoardView({ tiles = [], boardSize, players = [], children }) {
  const containerRef = useRef(null)
  const wrapperRef = useRef(null)
  const [dimensions, setDimensions] = useState({ width: 0, height: 0 })
  const [boardDimensions, setBoardDimensions] = useState({ width: 0, height: 0 })

  useEffect(() => {
    if (!wrapperRef.current) return

    const calculateSize = () => {
      const wrapper = wrapperRef.current
      if (!wrapper) return

      requestAnimationFrame(() => {
        const rect = wrapper.getBoundingClientRect()
        const availableWidth = Math.max(0, rect.width - 32)
        const availableHeight = Math.max(0, rect.height - 32)
        
        setBoardDimensions({
          width: availableWidth,
          height: availableHeight
        })
      })
    }

    const timeoutId = setTimeout(calculateSize, 0)
    const resizeObserver = new ResizeObserver(calculateSize)
    resizeObserver.observe(wrapperRef.current)

    const handleOrientationChange = () => {
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

  const tileWidth = dimensions.width > 0 ? dimensions.width / boardSize : 0
  const tileHeight = dimensions.height > 0 ? dimensions.height / boardSize : 0
  const tileSize = (tileWidth + tileHeight) / 2
  const isLandscape = boardDimensions.width > boardDimensions.height
  
  if (!boardSize || boardSize < 2) {
    return <div className="text-center p-8 font-zero animate-pulse">LOADING BOARD...</div>
  }

  const isOnPerimeter = (x, y) => x === 0 || x === boardSize - 1 || y === 0 || y === boardSize - 1
  
  const getTileEdge = (x, y) => {
    if (y === 0) return 'top'
    if (y === boardSize - 1) return 'bottom'
    if (x === 0) return 'left'
    if (x === boardSize - 1) return 'right'
    return null
  }

  return (
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
          width: boardDimensions.width > 0 ? `${boardDimensions.width}px` : '100%',
          height: boardDimensions.height > 0 ? `${boardDimensions.height}px` : '100%',
          maxWidth: '100%',
          maxHeight: '100%',
          flexShrink: 0,
        }}
      >
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
                width={tileWidth}
                height={tileHeight}
                size={tileSize}
                isLandscape={isLandscape}
                edge={getTileEdge(tile.x, tile.y)}
                boardSize={boardSize}
              />
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
            <div
              key={player.id}
              style={{
                gridColumn: tile.x + 1,
                gridRow: tile.y + 1,
                pointerEvents: 'none',
                zIndex: 20
              }}
              className="relative w-full h-full"
            >
               <PlayerToken
                  player={player}
                  tile={tile}
                  boardSize={boardSize}
                  tileWidth={tileWidth}
                  tileHeight={tileHeight}
                  tileSize={tileSize}
                  offsetX={(playerIndex % 2) * tokenOffset - tokenOffset / 2}
                  offsetY={Math.floor(playerIndex / 2) * tokenOffset - tokenOffset / 2}
                />
            </div>
          )
        })}

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
