const TILE_TYPE_COLORS = {
  PROPERTY: '#00ff00',
  TAX: '#ff0000',
  CHANCE: '#ffff00',
  TRAP: '#ff00ff',
  BUFF: '#00ffff',
  NEUTRAL: '#666666',
  GO: '#00ff00',
}

export default function TileComponent({ tile, players = [], width, height, size = 72, isLandscape = false, edge = null, boardSize = 0, style = {} }) {
  const owner = players.find(p => p.id === tile.owner_id)
  const isUnowned = !tile.owner_id
  const isPurchasable = tile.type === 'PROPERTY' && isUnowned
  const accentColor = TILE_TYPE_COLORS[tile.type] || TILE_TYPE_COLORS.NEUTRAL

  const tileWidth = width || size
  const tileHeight = height || size
  const baseTileSize = 72
  const scaleFactor = size / baseTileSize
  
  const typeFontSize = Math.max(4, Math.min(10, Math.round(7 * scaleFactor)))
  const nameFontSize = Math.max(5, Math.min(12, Math.round(8 * scaleFactor)))
  const detailFontSize = Math.max(4, Math.min(10, Math.round(7 * scaleFactor)))
  const rentFontSize = Math.max(3, Math.min(8, Math.round(6 * scaleFactor)))
  const borderWidth = Math.max(1, Math.min(4, Math.round(3 * scaleFactor)))
  const padding = Math.max(1, Math.min(4, Math.round(2 * scaleFactor)))
  
  const maxNameLength = size < 50 ? 4 : size < 70 ? 6 : size < 100 ? 8 : 12
  const contentWidth = tileWidth - (borderWidth * 2)
  const contentHeight = tileHeight - (borderWidth * 2)

  return (
    <div
      className="tile relative bg-sasta-white overflow-hidden"
      style={{
        width: `${tileWidth}px`,
        height: `${tileHeight}px`,
        border: `${borderWidth}px solid ${owner ? owner.color : '#000000'}`,
        borderStyle: isUnowned ? 'dashed' : 'solid',
        opacity: isUnowned ? 0.8 : 1,
        boxSizing: 'border-box',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...style,
      }}
    >
      <div
        className="tile-content relative bg-sasta-white"
        style={{
          width: `${contentWidth}px`,
          height: `${contentHeight}px`,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: `${padding}px`,
          boxSizing: 'border-box',
        }}
      >
        <div 
          className="w-full text-center font-zero font-bold text-sasta-black"
          style={{ 
            backgroundColor: accentColor, 
            fontSize: `${typeFontSize}px`, 
            lineHeight: 1.2, 
            padding: `${Math.max(1, Math.floor(padding / 2))}px 0` 
          }}
        >
          {tile.type === 'CHANCE' ? 'SASTA' : tile.type}
        </div>

        <div className="tile-name flex-1 flex items-center justify-center px-0.5 overflow-hidden w-full">
          <span 
            className="font-zero font-bold text-center leading-tight text-sasta-black"
            style={{ 
              fontSize: `${nameFontSize}px`, 
              wordBreak: 'break-word', 
              display: '-webkit-box', 
              WebkitLineClamp: size < 60 ? 1 : 2, 
              WebkitBoxOrient: 'vertical', 
              overflow: 'hidden',
              lineHeight: 1.1
            }}
          >
            {tile.name.toUpperCase()}
          </span>
        </div>

        <div className="w-full">
          {isPurchasable && tile.price > 0 && (
            <div 
              className="bg-sasta-black text-sasta-accent text-center font-zero font-bold"
              style={{ fontSize: `${detailFontSize}px`, padding: `${Math.max(1, Math.floor(padding / 2))}px 0` }}
            >
              ${tile.price}
            </div>
          )}

          {owner && (
            <div
              className="text-center font-zero font-bold text-sasta-white"
              style={{ 
                backgroundColor: owner.color, 
                fontSize: `${detailFontSize}px`, 
                padding: `${Math.max(1, Math.floor(padding / 2))}px 0` 
              }}
            >
              {owner.name.slice(0, maxNameLength).toUpperCase()}
            </div>
          )}

          {owner && tile.rent > 0 && size >= 60 && (
            <div 
              className="text-center font-zero text-sasta-black/60"
              style={{ fontSize: `${rentFontSize}px` }}
            >
              RENT: ${tile.rent}
            </div>
          )}

          {tile.type === 'GO' && (
            <div 
              className="bg-sasta-accent text-sasta-black text-center font-zero font-bold"
              style={{ fontSize: `${detailFontSize}px`, padding: `${Math.max(1, Math.floor(padding / 2))}px 0` }}
            >
              {'>> GO >>'}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}

export { TILE_TYPE_COLORS }
