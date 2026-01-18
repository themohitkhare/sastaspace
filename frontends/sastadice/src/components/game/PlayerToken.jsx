const DEFAULT_TILE_SIZE = 72

export default function PlayerToken({
  player,
  tile,
  boardSize,
  tileWidth,
  tileHeight,
  tileSize = DEFAULT_TILE_SIZE,
  totalOnTile = 1,
  offsetX = 0,
  offsetY = 0
}) {
  if (!tile) return null

  const isOnPerimeter = tile.x === 0 || tile.x === boardSize - 1 || tile.y === 0 || tile.y === boardSize - 1
  if (!isOnPerimeter) return null

  const playerColor = player.color || '#000000'
  const actualTileWidth = tileWidth || tileSize
  const actualTileHeight = tileHeight || tileSize
  const sizeFactor = totalOnTile > 2 ? 0.8 : totalOnTile > 1 ? 0.9 : 1
  const tokenSize = Math.max(12, Math.min(40, Math.floor(tileSize / 2.5 * sizeFactor)))
  const fontSize = Math.max(6, Math.min(16, Math.floor(tokenSize / 2.2)))
  const borderWidth = Math.max(2, Math.min(3, Math.floor(tokenSize / 14)))

  return (
    <div
      className="player-token absolute font-data font-bold text-white"
      style={{
        gridColumn: tile.x + 1,
        gridRow: tile.y + 1,
        transform: `translate(${actualTileWidth / 2 - tokenSize / 2 + offsetX}px, ${actualTileHeight / 2 - tokenSize / 2 + offsetY}px)`,
        backgroundColor: playerColor,
        width: `${tokenSize}px`,
        height: `${tokenSize}px`,
        borderRadius: '50%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        fontSize: `${fontSize}px`,
        border: `${borderWidth}px solid #FFF`,
        boxShadow: '0 2px 4px rgba(0,0,0,0.4)',
        outline: '1px solid #000',
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

