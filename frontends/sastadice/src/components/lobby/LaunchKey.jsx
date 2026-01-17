import { useState } from 'react'

// Convert hex to RGB for CSS manipulation
function hexToRgb(hex) {
  const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex)
  return result ? {
    r: parseInt(result[1], 16),
    g: parseInt(result[2], 16),
    b: parseInt(result[3], 16)
  } : { r: 200, g: 200, b: 200 }
}

// Generate lighter/darker shades
function adjustBrightness(hex, percent) {
  const { r, g, b } = hexToRgb(hex)
  const adjust = (c) => Math.min(255, Math.max(0, Math.round(c + (255 * percent / 100))))
  return `rgb(${adjust(r)}, ${adjust(g)}, ${adjust(b)})`
}

export default function LaunchKey({ isReady, isLoading, onToggle, playerName, playerColor = '#FFB800' }) {
  const [isAnimating, setIsAnimating] = useState(false)

  const handleClick = () => {
    if (isLoading) return
    setIsAnimating(true)
    onToggle()
    setTimeout(() => setIsAnimating(false), 600)
  }

  // Generate key color variations from player color
  const keyLight = adjustBrightness(playerColor, 20)
  const keyBase = playerColor
  const keyDark = adjustBrightness(playerColor, -20)
  const keyDarker = adjustBrightness(playerColor, -35)

  return (
    <button
      onClick={handleClick}
      disabled={isLoading}
      className="launch-key-container group relative w-full py-8 bg-gradient-to-b from-zinc-800 to-zinc-900 border-4 border-zinc-700 rounded-lg shadow-[inset_0_2px_10px_rgba(0,0,0,0.5)] disabled:opacity-50 overflow-hidden"
      aria-label={isReady ? 'Key turned - Ready' : 'Turn key to ready up'}
    >
      <div className="absolute inset-0 opacity-10 bg-[radial-gradient(circle_at_50%_50%,white_1px,transparent_1px)] bg-[length:4px_4px]" />
      
      <div className="absolute top-3 right-3 flex items-center gap-2">
        <span className="font-zero text-[10px] text-zinc-500 uppercase tracking-wider">STATUS</span>
        <div 
          className={`w-3 h-3 rounded-full transition-all duration-500 ${
            isReady 
              ? 'bg-green-500 shadow-[0_0_10px_#22c55e,0_0_20px_#22c55e]' 
              : 'bg-red-500 shadow-[0_0_6px_#ef4444]'
          }`}
        />
      </div>

      <div className="absolute top-3 left-3 flex items-center gap-2">
        <div 
          className="w-4 h-4 border-2 border-zinc-600"
          style={{ backgroundColor: playerColor }}
        />
        <div>
          <span className="font-zero text-[10px] text-zinc-500 uppercase tracking-wider">OPERATOR</span>
          <div className="font-zero text-xs font-bold" style={{ color: keyLight }}>{playerName?.toUpperCase()}</div>
        </div>
      </div>

      {/* Key mechanism */}
      <div className="flex flex-col items-center justify-center mt-4">
        {/* Keyhole housing */}
        <div className="relative">
          {/* Outer ring */}
          <div className="w-24 h-24 rounded-full bg-gradient-to-b from-zinc-600 to-zinc-800 p-1 shadow-[0_4px_15px_rgba(0,0,0,0.5)]">
            {/* Inner ring */}
            <div className="w-full h-full rounded-full bg-gradient-to-b from-zinc-700 to-zinc-900 flex items-center justify-center shadow-[inset_0_2px_10px_rgba(0,0,0,0.8)]">
              {/* Keyhole slot */}
              <div className="relative w-16 h-16">
                <div 
                  className={`absolute inset-0 flex items-center justify-center transition-transform duration-500 ease-out ${
                    isReady ? 'rotate-90' : 'rotate-0'
                  } ${isAnimating ? 'scale-95' : 'scale-100'}`}
                >
                  <div className="relative">
                    {/* Key grip (top part) - uses player color */}
                    <div 
                      className="w-8 h-12 rounded-t-full shadow-[2px_2px_4px_rgba(0,0,0,0.4)]"
                      style={{ 
                        background: `linear-gradient(to bottom, ${keyLight}, ${keyBase}, ${keyDark})`,
                        border: `1px solid ${keyDarker}`
                      }}
                    >
                      <div className="absolute top-2 left-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-gradient-to-b from-zinc-800 to-zinc-900 shadow-[inset_0_1px_3px_rgba(0,0,0,0.8)]" />
                      <div 
                        className="absolute bottom-1 left-1/2 -translate-x-1/2 w-5 h-1 rounded opacity-30"
                        style={{ backgroundColor: keyDarker }}
                      />
                      <div 
                        className="absolute bottom-3 left-1/2 -translate-x-1/2 w-5 h-1 rounded opacity-30"
                        style={{ backgroundColor: keyDarker }}
                      />
                    </div>
                    {/* Key shaft */}
                    <div 
                      className="w-3 h-6 mx-auto shadow-[1px_2px_3px_rgba(0,0,0,0.3)]"
                      style={{ background: `linear-gradient(to right, ${keyDark}, ${keyLight}, ${keyDark})` }}
                    >
                      <div 
                        className="absolute -right-1 bottom-1 w-2 h-2"
                        style={{ backgroundColor: keyBase }}
                      />
                      <div 
                        className="absolute -right-1 bottom-3 w-1.5 h-1.5"
                        style={{ backgroundColor: keyBase }}
                      />
                    </div>
                  </div>
                </div>

                {/* Center dot marker */}
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-2 h-2 rounded-full bg-zinc-900 shadow-[inset_0_1px_2px_rgba(0,0,0,0.5)]" />
              </div>
            </div>
          </div>

          {/* Position markers */}
          <div className="absolute -left-8 top-1/2 -translate-y-1/2 font-zero text-[10px] text-zinc-500 font-bold">OFF</div>
          <div className="absolute -bottom-6 left-1/2 -translate-x-1/2 font-zero text-[10px] text-green-500 font-bold">ARM</div>
        </div>

        {/* Instructions */}
        <div className="mt-8 text-center">
          <div className={`font-zero text-sm font-bold transition-colors duration-300 ${isReady ? 'text-green-400' : 'text-zinc-400'}`}>
            {isLoading ? 'TURNING...' : isReady ? '✓ ARMED' : 'TURN TO ARM'}
          </div>
          <div className="font-zero text-[10px] text-zinc-600 mt-1">
            {isReady ? 'WAITING FOR OTHER OPERATORS' : 'CLICK TO TURN KEY'}
          </div>
        </div>
      </div>

      {/* Scan lines effect */}
      <div className="absolute inset-0 pointer-events-none opacity-5 bg-[repeating-linear-gradient(0deg,transparent,transparent_2px,rgba(255,255,255,0.1)_2px,rgba(255,255,255,0.1)_4px)]" />
    </button>
  )
}
