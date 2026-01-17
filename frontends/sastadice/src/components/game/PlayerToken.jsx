const DEFAULT_TILE_SIZE = 72

export default function PlayerToken({ 
  player, 
  tile, 
  boardSize,
  tileSize = DEFAULT_TILE_SIZE,
  offsetX = 0, 
  offsetY = 0 
}) {
  if (!tile) return null

  const isOnPerimeter = tile.x === 0 || tile.x === boardSize - 1 || tile.y === 0 || tile.y === boardSize - 1
  if (!isOnPerimeter) return null

  const playerColor = player.color || '#000000'
  const tokenSize = Math.max(12, Math.min(40, Math.floor(tileSize / 3)))
  const fontSize = Math.max(6, Math.min(16, Math.floor(tokenSize / 2.4)))
  const borderWidth = Math.max(1, Math.min(3, Math.floor(tokenSize / 20)))

  return (
    <div
      className="player-token absolute font-zero font-bold text-sasta-white"
      style={{
        gridColumn: tile.x + 1,
        gridRow: tile.y + 1,
        transform: `translate(${tileSize / 2 - tokenSize / 2 + offsetX}px, ${tileSize / 2 - tokenSize / 2 + offsetY}px)`,
        backgroundColor: playerColor,
        width: `${tokenSize}px`,
        height: `${tokenSize}px`,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: `${fontSize}px`,
        border: `${borderWidth}px solid #000`,
        zIndex: 20,
        pointerEvents: 'none',
      }}
      title={`${player.name} - $${player.cash}`}
    >
      {player.name.charAt(0).toUpperCase()}
    </div>
  )
}

export { DEFAULT_TILE_SIZE as TILE_SIZE }
