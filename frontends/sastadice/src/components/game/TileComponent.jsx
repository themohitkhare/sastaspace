const TILE_TYPE_COLORS = {
  PROPERTY: '#00ff00',
  TAX: '#ff0000',
  CHANCE: '#ffff00',
  TRAP: '#ff00ff',
  BUFF: '#00ffff',
  NEUTRAL: '#666666',
  GO: '#00ff00',
  NODE: '#ff6600',
  GO_TO_JAIL: '#ff0000',
  TELEPORT: '#9900ff',
  MARKET: '#ff00ff',
  JAIL: '#888888',
}

export default function TileComponent({ tile, players = [], width, height, size = 72, isLandscape = false, edge = null, boardSize = 0, style = {}, isBlocked = false, isDdosTarget = false, onClick, blockedRoundsRemaining = null, isFreeLanding = false }) {
  const isClickable = tile.type === 'PROPERTY' && onClick
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
  const ownerBgColor = owner ? `${owner.color}33` : 'transparent'
  const ownerBorderWidth = owner ? Math.max(2, borderWidth + 1) : borderWidth

  const blockedOverlay = isBlocked ? {
    backgroundColor: 'rgba(255, 0, 0, 0.4)',
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    zIndex: 5,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    pointerEvents: 'none',
  } : null

  const ddosHighlight = isDdosTarget ? {
    boxShadow: '0 0 8px 2px #ff00ff',
    border: `${ownerBorderWidth + 2}px solid #ff00ff`,
  } : {}

  return (
    <div
      className={`tile relative overflow-hidden ${isClickable ? 'cursor-pointer hover:brightness-110 transition-all' : ''}`}
      onClick={isClickable ? () => onClick(tile) : undefined}
      style={{
        width: `${tileWidth}px`,
        height: `${tileHeight}px`,
        border: `${ownerBorderWidth}px solid ${owner ? owner.color : '#000000'}`,
        borderStyle: isUnowned ? 'dashed' : 'solid',
        backgroundColor: owner ? ownerBgColor : '#FFFFFF',
        boxSizing: 'border-box',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        ...ddosHighlight,
        ...style,
      }}
    >
      {isBlocked && (
        <div style={blockedOverlay}>
          <div
            className="font-zero font-bold text-white"
            style={{
              fontSize: `${Math.max(6, Math.round(8 * scaleFactor))}px`,
              textShadow: '1px 1px 2px #000',
            }}
          >
            {'BLOCKED' + (blockedRoundsRemaining > 0 ? ` (${blockedRoundsRemaining})` : '')}
          </div>
        </div>
      )}
      {tile.upgrade_level > 0 && size >= 50 && (
        <div
          className={`absolute flex items-center gap-0.5 ${
            tile.upgrade_level === 2 ? 'animate-pulse' : ''
          }`}
          style={{
            top: '2px',
            left: '2px',
            zIndex: 10,
          }}
          role="status"
          aria-label={`Upgrade level ${tile.upgrade_level}: ${
            tile.upgrade_level === 1 ? 'Script Kiddie' : 'Elite Hacker'
          }`}
        >
          {/* LED indicator */}
          <div
            className={`rounded-full ${
              tile.upgrade_level === 1
                ? 'bg-green-500 w-2 h-2'
                : 'bg-yellow-400 w-3 h-3 shadow-[0_0_8px_#fbbf24]'
            }`}
            aria-hidden="true"
          />
          {/* Level badge */}
          <span
            className="font-zero font-bold text-white bg-black/70 px-0.5 rounded"
            style={{ fontSize: `${Math.max(7, Math.round(9 * scaleFactor))}px` }}
          >
            L{tile.upgrade_level}
          </span>
        </div>
      )}

      {/* NODE tile indicator */}
      {tile.type === 'NODE' && size >= 50 && (
        <div
          className="absolute bottom-1 right-1 text-[8px] font-bold text-cyan-400"
          aria-label="Server Node"
          style={{ fontSize: `${Math.max(6, Math.round(8 * scaleFactor))}px` }}
        >
          NODE
        </div>
      )}
      {isFreeLanding && size >= 50 && (
        <div
          className="absolute bottom-1 left-1 font-zero font-bold text-green-400"
          style={{
            fontSize: `${Math.max(6, Math.round(8 * scaleFactor))}px`,
            textShadow: '1px 1px 1px #000',
          }}
        >
          FREE
        </div>
      )}
      {owner && size >= 50 && (
        <div
          className="absolute font-zero font-bold text-white flex items-center justify-center"
          style={{
            top: '2px',
            right: '2px',
            width: `${Math.max(10, Math.round(14 * scaleFactor))}px`,
            height: `${Math.max(10, Math.round(14 * scaleFactor))}px`,
            backgroundColor: owner.color,
            border: '1px solid #000',
            fontSize: `${Math.max(6, Math.round(8 * scaleFactor))}px`,
            zIndex: 10,
          }}
        >
          {owner.name?.charAt(0)?.toUpperCase()}
        </div>
      )}

      <div
        className="tile-content relative"
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
