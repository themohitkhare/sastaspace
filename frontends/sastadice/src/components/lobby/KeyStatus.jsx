export default function KeyStatus({ player, isMe, isHost, canKick, onKick }) {
  const keyColor = player.color || '#FFB800'
  
  return (
    <div 
      className={`flex items-center gap-3 p-3 border-2 transition-all duration-300 ${
        player.ready 
          ? 'border-green-500 bg-green-500/10' 
          : 'border-zinc-700 bg-zinc-800/50'
      } ${isMe ? 'ring-2 ring-sasta-accent ring-offset-2 ring-offset-black' : ''}`}
    >
      <div className="relative w-10 h-10 rounded-full bg-gradient-to-b from-zinc-600 to-zinc-800 flex items-center justify-center shadow-[inset_0_2px_4px_rgba(0,0,0,0.5)]">
        <div 
          className={`w-4 h-6 transition-transform duration-500 ease-out ${player.ready ? 'rotate-90' : 'rotate-0'}`}
        >
          <div 
            className="w-full h-4 rounded-t-full"
            style={{ background: `linear-gradient(to bottom, ${keyColor}, ${keyColor}dd)` }}
          />
          <div 
            className="w-1.5 h-2 mx-auto"
            style={{ backgroundColor: keyColor }}
          />
        </div>
        
        <div 
          className={`absolute -top-1 -right-1 w-3 h-3 rounded-full border-2 border-zinc-900 transition-all duration-300 ${
            player.ready 
              ? 'bg-green-500 shadow-[0_0_6px_#22c55e]' 
              : 'bg-zinc-600'
          }`}
        />
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-zero text-sm font-bold text-zinc-200 truncate">
            {player.name.toUpperCase()}
          </span>
          {isHost && (
            <span className="font-zero text-[10px] bg-amber-500 text-black px-1.5 py-0.5">HOST</span>
          )}
          {isMe && (
            <span className="font-zero text-[10px] bg-sasta-accent text-black px-1.5 py-0.5">YOU</span>
          )}
        </div>
        <div className={`font-zero text-[10px] transition-colors ${player.ready ? 'text-green-400' : 'text-zinc-500'}`}>
          {player.ready ? '✓ KEY ARMED' : 'STANDING BY'}
        </div>
      </div>

      <div 
        className="w-4 h-4 border-2 border-black shadow-sm"
        style={{ backgroundColor: player.color }}
      />

      {canKick && !isMe && (
        <button
          onClick={() => onKick(player.id)}
          className="w-8 h-8 flex items-center justify-center bg-red-500 hover:bg-red-600 text-white font-bold border-2 border-black transition-colors"
          title={`Kick ${player.name}`}
        >
          ✕
        </button>
      )}
    </div>
  )
}
