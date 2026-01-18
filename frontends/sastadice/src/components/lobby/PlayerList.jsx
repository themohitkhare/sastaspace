export default function PlayerList({ players, currentPlayerId }) {
  if (!players || players.length === 0) {
    return (
      <div className="border-brutal-sm p-6 text-center">
        <p className="font-zero text-sasta-black/60">NO PLAYERS YET...</p>
        <p className="font-zero text-sm mt-2 text-sasta-black/40">BE THE FIRST TO JOIN!</p>
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {players.map((player, index) => {
        const isMe = player.id === currentPlayerId

        return (
          <div
            key={player.id}
            className={`border-brutal-sm p-4 flex items-center gap-4 ${
              isMe ? 'bg-sasta-accent' : 'bg-sasta-white'
            }`}
          >
            <div className="font-zero font-bold text-2xl w-10 text-center">
              {String(index + 1).padStart(2, '0')}
            </div>

            <div
              className="w-10 h-10 border-brutal-sm flex items-center justify-center font-zero font-bold text-sasta-white"
              style={{ backgroundColor: player.color || '#000000' }}
            >
              {player.name.charAt(0).toUpperCase()}
            </div>

            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <span className="font-zero font-bold truncate">{player.name.toUpperCase()}</span>
                {isMe && (
                  <span className="font-zero text-xs bg-sasta-black text-sasta-accent px-2 py-0.5">YOU</span>
                )}
                {player.name.startsWith('CPU') && (
                  <span className="font-zero text-xs bg-sasta-black/60 text-sasta-white px-2 py-0.5">CPU</span>
                )}
              </div>
              <div className="text-sm font-zero opacity-60">
                {player.submitted_tiles?.length || 0} TILES
              </div>
            </div>

            <div className={`text-2xl transition-transform ${player.ready ? 'rotate-90' : 'opacity-30'}`}>
              🔑
            </div>
          </div>
        )
      })}
    </div>
  )
}
