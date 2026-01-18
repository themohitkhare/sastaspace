export default function PlayerPanel({
  players = [],
  currentTurnPlayerId,
  currentPlayerId,
  tiles = [],
  onTradeClick
}) {
  return (
    <div className="player-panel w-full">
      <h3 className="text-sm font-zero font-bold mb-3">PLAYERS</h3>
      <div className="space-y-2">
        {players.map((player) => {
          const isCurrentTurn = player.id === currentTurnPlayerId
          const isMe = player.id === currentPlayerId
          const ownedTiles = tiles.filter(t => t.owner_id === player.id)

          return (
            <div
              key={player.id}
              className={`border-brutal-sm p-2 ${isCurrentTurn ? 'bg-sasta-accent' : 'bg-sasta-white'
                }`}
            >
              <div className="flex items-center gap-2">
                <div
                  className="w-7 h-7 flex items-center justify-center font-zero font-bold text-sasta-white text-xs border-2 border-sasta-black"
                  style={{ backgroundColor: player.color || '#000000' }}
                >
                  {player.name.charAt(0).toUpperCase()}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1">
                    <span className="font-zero font-bold text-xs truncate">
                      {player.name.toUpperCase()}
                    </span>
                    {isMe && (
                      <span className="font-zero text-[8px] bg-sasta-black text-sasta-accent px-1">
                        YOU
                      </span>
                    )}
                    {isCurrentTurn && (
                      <span className="font-zero text-[8px] bg-sasta-black text-sasta-white px-1 animate-pulse">
                        {'>>'}
                      </span>
                    )}
                  </div>
                </div>

                <div className="text-right">
                  <div className="font-zero font-bold text-sm text-sasta-black">
                    ${player.cash.toLocaleString()}
                  </div>
                  {!isMe && onTradeClick && (
                    <button
                      onClick={() => onTradeClick(player)}
                      className="mt-1 block ml-auto bg-sasta-accent border border-black px-1.5 py-0.5 text-[9px] font-bold font-zero shadow-brutal-sm hover:shadow-none hover:translate-x-0.5 hover:translate-y-0.5 transition-all"
                    >
                      TRADE
                    </button>
                  )}
                </div>
              </div>

              {ownedTiles.length > 0 && (
                <div className="mt-1 flex flex-wrap gap-1">
                  {ownedTiles.slice(0, 3).map((tile) => (
                    <div
                      key={tile.id}
                      className="font-zero text-[7px] px-1 py-0.5 bg-sasta-black text-sasta-white truncate max-w-[50px]"
                      title={tile.name}
                    >
                      {tile.name.slice(0, 6).toUpperCase()}
                    </div>
                  ))}
                  {ownedTiles.length > 3 && (
                    <div className="font-zero text-[7px] px-1 py-0.5 bg-sasta-black/60 text-sasta-white">
                      +{ownedTiles.length - 3}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
