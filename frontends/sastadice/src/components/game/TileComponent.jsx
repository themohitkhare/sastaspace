const TILE_TYPE_COLORS = {
  PROPERTY: '#00ff00',
  TAX: '#ff0000',
  CHANCE: '#ffff00',
  TRAP: '#ff00ff',
  BUFF: '#00ffff',
  NEUTRAL: '#666666',
  GO: '#00ff00',
}

export default function TileComponent({ tile, players = [], style = {} }) {
  const owner = players.find(p => p.id === tile.owner_id)
  const isUnowned = !tile.owner_id
  const isPurchasable = tile.type === 'PROPERTY' && isUnowned

  // Tile type determines accent color
  const accentColor = TILE_TYPE_COLORS[tile.type] || TILE_TYPE_COLORS.NEUTRAL

  return (
    <div
      className="tile relative bg-sasta-white"
      style={{
        width: '72px',
        height: '72px',
        border: `3px solid ${owner ? owner.color : '#000000'}`,
        borderStyle: isUnowned ? 'dashed' : 'solid',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '2px',
        opacity: isUnowned ? 0.8 : 1,
        ...style,
      }}
    >
      <div 
        className="w-full px-1 py-0.5 text-center font-zero text-[7px] font-bold text-sasta-black"
        style={{ backgroundColor: accentColor }}
      >
        {tile.type === 'CHANCE' ? 'SASTA' : tile.type}
      </div>

      <div className="tile-name flex-1 flex items-center justify-center px-1">
        <span className="font-zero text-[8px] font-bold text-center leading-tight text-sasta-black truncate w-full">
          {tile.name.toUpperCase()}
        </span>
      </div>

      <div className="w-full">
        {isPurchasable && tile.price > 0 && (
          <div className="bg-sasta-black text-sasta-accent text-center font-zero text-[8px] font-bold py-0.5">
            ${tile.price}
          </div>
        )}

        {owner && (
          <div
            className="text-center font-zero text-[8px] font-bold py-0.5 text-sasta-white"
            style={{ backgroundColor: owner.color }}
          >
            {owner.name.slice(0, 6).toUpperCase()}
          </div>
        )}

        {owner && tile.rent > 0 && (
          <div className="text-center font-zero text-[6px] text-sasta-black/60">
            RENT: ${tile.rent}
          </div>
        )}

        {tile.type === 'GO' && (
          <div className="bg-sasta-accent text-sasta-black text-center font-zero text-[8px] font-bold py-0.5">
            {'>> GO >>'}
          </div>
        )}
      </div>
    </div>
  )
}

export { TILE_TYPE_COLORS }
