const TILE_TYPE_COLORS = {
  PROPERTY: '#00ff00',
  TAX: '#ff0000',
  CHANCE: '#ffff00',
  TRAP: '#ff00ff',
  BUFF: '#00ffff',
  NEUTRAL: '#666666',
  GO: '#00ff00',
}

export default function TileComponent({ tile, players = [], size = 72, style = {} }) {
  const owner = players.find(p => p.id === tile.owner_id)
  const isUnowned = !tile.owner_id
  const isPurchasable = tile.type === 'PROPERTY' && isUnowned
  const accentColor = TILE_TYPE_COLORS[tile.type] || TILE_TYPE_COLORS.NEUTRAL

  const isSmall = size < 60
  const fontSize = isSmall ? '5px' : '7px'
  const nameFontSize = isSmall ? '6px' : '8px'

  return (
    <div
      className="tile relative bg-sasta-white"
      style={{
        width: `${size}px`,
        height: `${size}px`,
        border: `${isSmall ? 2 : 3}px solid ${owner ? owner.color : '#000000'}`,
        borderStyle: isUnowned ? 'dashed' : 'solid',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: isSmall ? '1px' : '2px',
        opacity: isUnowned ? 0.8 : 1,
        ...style,
      }}
    >
      <div 
        className="w-full px-0.5 text-center font-zero font-bold text-sasta-black"
        style={{ backgroundColor: accentColor, fontSize, lineHeight: 1.2, padding: isSmall ? '1px 0' : '2px 0' }}
      >
        {tile.type === 'CHANCE' ? 'SASTA' : tile.type}
      </div>

      <div className="tile-name flex-1 flex items-center justify-center px-0.5 overflow-hidden">
        <span 
          className="font-zero font-bold text-center leading-tight text-sasta-black"
          style={{ fontSize: nameFontSize, wordBreak: 'break-word', display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden' }}
        >
          {tile.name.toUpperCase()}
        </span>
      </div>

      <div className="w-full">
        {isPurchasable && tile.price > 0 && (
          <div 
            className="bg-sasta-black text-sasta-accent text-center font-zero font-bold"
            style={{ fontSize: nameFontSize, padding: '1px 0' }}
          >
            ${tile.price}
          </div>
        )}

        {owner && (
          <div
            className="text-center font-zero font-bold text-sasta-white"
            style={{ backgroundColor: owner.color, fontSize: nameFontSize, padding: '1px 0' }}
          >
            {owner.name.slice(0, isSmall ? 4 : 6).toUpperCase()}
          </div>
        )}

        {owner && tile.rent > 0 && !isSmall && (
          <div className="text-center font-zero text-[6px] text-sasta-black/60">
            RENT: ${tile.rent}
          </div>
        )}

        {tile.type === 'GO' && (
          <div 
            className="bg-sasta-accent text-sasta-black text-center font-zero font-bold"
            style={{ fontSize: nameFontSize, padding: '1px 0' }}
          >
            {'>> GO >>'}
          </div>
        )}
      </div>
    </div>
  )
}

export { TILE_TYPE_COLORS }
