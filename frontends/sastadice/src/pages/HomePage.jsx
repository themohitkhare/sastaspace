import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/apiClient'
import { useGameStore } from '../store/useGameStore'

const CPU_CHARACTERS = [
  { id: 'cpu1', name: 'ROBOCOP', color: '#FF6B6B', emoji: '🤖' },
  { id: 'cpu2', name: 'CHAD BOT', color: '#4ECDC4', emoji: '💪' },
  { id: 'cpu3', name: 'KAREN.EXE', color: '#FF69B4', emoji: '💅' },
  { id: 'cpu4', name: 'STONKS', color: '#45B7D1', emoji: '📈' },
]

export default function HomePage() {
  const navigate = useNavigate()
  const setGameId = useGameStore((s) => s.setGameId)
  const setGame = useGameStore((s) => s.setGame)
  const reset = useGameStore((s) => s.reset)
  const [gameCode, setGameCode] = useState('')
  const [selectedCpus, setSelectedCpus] = useState([])
  const [showAdvanced, setShowAdvanced] = useState(false)
  const [isCreating, setIsCreating] = useState(false)
  const [isJoining, setIsJoining] = useState(false)

  const toggleCpu = (cpuId) => {
    setSelectedCpus(prev =>
      prev.includes(cpuId)
        ? prev.filter(id => id !== cpuId)
        : [...prev, cpuId]
    )
  }

  const handleCreateGame = async () => {
    setIsCreating(true)
    reset()
    try {
      const res = await apiClient.post(`/sastadice/games?cpu_count=${selectedCpus.length}`)
      const newGameId = res.data.id
      setGameId(newGameId)
      setGame(res.data, 0)
      navigate(`/lobby/${newGameId}`)
    } catch (err) {
      alert('Failed to create game. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  const handleJoinGame = async () => {
    const cleanGameCode = gameCode.trim()
    if (!cleanGameCode) {
      alert('Please enter a game code')
      return
    }

    setIsJoining(true)
    reset()
    try {
      const res = await apiClient.get(`/sastadice/games/${cleanGameCode}`)
      const joinedGameId = res.data.id
      setGameId(joinedGameId)
      setGame(res.data, 0)
      navigate(`/lobby/${joinedGameId}`)
    } catch (err) {
      if (err.response?.status === 404) {
        alert('Game not found. Please check the game code.')
      } else {
        alert('Failed to join game. Please try again.')
      }
    } finally {
      setIsJoining(false)
    }
  }

  return (
    <div className="min-h-screen bg-sasta-white flex flex-col overflow-auto">
      <div className="text-center py-4 px-4 shrink-0">
        <h1 className="text-4xl sm:text-5xl lg:text-6xl font-bold font-zero tracking-tight">
          SASTADICE
        </h1>
        <p className="text-sm sm:text-base font-zero font-bold text-sasta-black/70 mt-1">
          ROLL THE DICE. BUILD THE BOARD. EMBRACE THE CHAOS.
        </p>
      </div>

      <div className="flex-1 flex items-center justify-center p-4">
        <div className="w-full max-w-5xl">
          <div className="border-brutal-sm bg-sasta-black text-sasta-white p-3 shadow-brutal-sm mb-4 hidden lg:block">
            <div className="flex justify-center gap-8 font-zero text-sm text-sasta-accent">
              <span>{'>'} MULTIPLAYER BOARD GAME</span>
              <span>{'>'} DYNAMIC ECONOMY</span>
              <span>{'>'} SASTA EVENTS</span>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
            <div className="border-brutal-sm bg-sasta-white p-4 shadow-brutal-sm">
              <h2 className="font-zero font-bold text-lg mb-3 border-b-2 border-sasta-black pb-2">
                🎮 CREATE NEW GAME
              </h2>

              <div className="mb-3">
                <button
                  type="button"
                  onClick={() => setShowAdvanced((v) => !v)}
                  aria-expanded={showAdvanced}
                  aria-controls="cpu-advanced-panel"
                  className={`w-full border-brutal-sm bg-sasta-white px-3 py-2 font-zero font-bold text-xs shadow-brutal-sm transition-all hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none ${showAdvanced ? 'translate-x-0.5 translate-y-0.5 shadow-none' : ''
                    }`}
                >
                  <div className="flex items-center justify-between gap-3">
                    <span className="opacity-80">{'> '}ADVANCED: ADD CPU OPPONENTS</span>
                    <span className="text-sasta-black/70">{showAdvanced ? '−' : '+'}</span>
                  </div>
                  <div className="mt-1 text-[10px] font-zero font-bold text-sasta-black/50 text-left">
                    {selectedCpus.length === 0
                      ? 'NONE SELECTED (MULTIPLAYER ONLY)'
                      : `${selectedCpus.length} CPU${selectedCpus.length > 1 ? 'S' : ''} SELECTED`}
                  </div>
                </button>

                {showAdvanced && (
                  <div className="mt-3" id="cpu-advanced-panel">
                    <label className="font-zero font-bold text-xs mb-2 block opacity-70">SELECT CPU OPPONENTS:</label>
                    <div className="grid grid-cols-2 gap-2">
                      {CPU_CHARACTERS.map((cpu) => {
                        const isSelected = selectedCpus.includes(cpu.id)
                        return (
                          <button
                            key={cpu.id}
                            onClick={() => toggleCpu(cpu.id)}
                            className={`p-2 border-brutal-sm transition-all text-left ${isSelected
                                ? 'shadow-none translate-x-0.5 translate-y-0.5'
                                : 'shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5'
                              }`}
                            style={{
                              backgroundColor: isSelected ? cpu.color : '#FFFFFF',
                              borderColor: cpu.color,
                              borderWidth: '2px',
                            }}
                          >
                            <div className="flex items-center gap-2">
                              <span className="text-xl">{cpu.emoji}</span>
                              <div>
                                <div
                                  className="font-zero font-bold text-xs"
                                  style={{ color: isSelected ? '#000' : cpu.color }}
                                >
                                  {cpu.name}
                                </div>
                                <div className="font-zero text-[9px] text-sasta-black/50">
                                  {isSelected ? '✓ ADDED' : 'TAP TO ADD'}
                                </div>
                              </div>
                            </div>
                          </button>
                        )
                      })}
                    </div>
                    <p className="font-zero text-[10px] text-sasta-black/50 mt-2 text-center">
                      TAP CPUs TO ADD / REMOVE
                    </p>
                  </div>
                )}
              </div>

              <button
                onClick={handleCreateGame}
                disabled={isCreating || isJoining}
                className="w-full min-h-[48px] border-brutal-sm bg-sasta-accent text-sasta-black px-4 py-3 font-zero font-bold text-base shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {isCreating ? '> CREATING...' : '> CREATE GAME'}
              </button>
            </div>

            <div className="border-brutal-sm bg-sasta-white p-4 shadow-brutal-sm flex flex-col">
              <h2 className="font-zero font-bold text-lg mb-3 border-b-2 border-sasta-black pb-2">
                🔗 JOIN EXISTING GAME
              </h2>

              <div className="flex-1 flex flex-col justify-center">
                <label className="font-zero font-bold text-xs mb-2 block opacity-70">GAME CODE:</label>
                <input
                  type="text"
                  value={gameCode}
                  onChange={(e) => setGameCode(e.target.value.toUpperCase())}
                  placeholder="PASTE OR TYPE CODE..."
                  className="w-full p-3 border-brutal-sm bg-sasta-white font-zero text-base placeholder:text-sasta-black/30 mb-3 uppercase"
                  onKeyPress={(e) => {
                    if (e.key === 'Enter' && gameCode.trim()) handleJoinGame()
                  }}
                />

                <button
                  onClick={handleJoinGame}
                  disabled={isJoining || isCreating || !gameCode.trim()}
                  className="w-full min-h-[48px] border-brutal-sm bg-sasta-black text-sasta-white px-4 py-3 font-zero font-bold text-base shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  {isJoining ? '> JOINING...' : '> JOIN GAME'}
                </button>

                <p className="font-zero text-[10px] text-sasta-black/50 mt-3 text-center">
                  GET THE CODE FROM THE GAME HOST
                </p>
              </div>
            </div>
          </div>

          <div className="border-brutal-sm bg-sasta-black text-sasta-white p-3 shadow-brutal-sm mt-4 lg:hidden">
            <div className="flex flex-wrap justify-center gap-4 font-zero text-xs text-sasta-accent">
              <span>{'>'} MULTIPLAYER</span>
              <span>{'>'} DYNAMIC ECONOMY</span>
              <span>{'>'} SASTA EVENTS</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

