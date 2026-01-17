import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/apiClient'
import { useGameStore } from '../store/useGameStore'

export default function HomePage() {
  const navigate = useNavigate()
  const setGameId = useGameStore((s) => s.setGameId)
  const setGame = useGameStore((s) => s.setGame)
  const reset = useGameStore((s) => s.reset)
  const [gameCode, setGameCode] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isJoining, setIsJoining] = useState(false)

  const handleCreateGame = async () => {
    setIsCreating(true)
    reset()
    try {
      const res = await apiClient.post('/sastadice/games')
      setGameId(res.data.id)
      setGame(res.data, 0)
      navigate('/lobby')
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
      setGameId(res.data.id)
      setGame(res.data, 0)
      navigate('/lobby')
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
    <div className="min-h-screen bg-sasta-white flex flex-col items-center justify-center p-8">
      <div className="max-w-lg w-full space-y-8">
        <div className="text-center">
          <h1 className="text-6xl md:text-8xl font-bold font-zero mb-4 tracking-tight">
            SASTADICE
          </h1>
          <p className="text-xl font-zero font-bold text-sasta-black/80">
            ROLL THE DICE. BUILD THE BOARD. EMBRACE THE CHAOS.
          </p>
        </div>

        <div className="border-brutal-lg bg-sasta-black text-sasta-white p-6 shadow-brutal-lg">
          <p className="font-zero text-sasta-accent">{'>'} MULTIPLAYER BOARD GAME</p>
          <p className="font-zero text-sasta-accent mt-1">{'>'} DYNAMIC ECONOMY</p>
          <p className="font-zero text-sasta-accent mt-1">{'>'} SASTA EVENTS</p>
        </div>

        <div className="space-y-6">
          <button
            onClick={handleCreateGame}
            disabled={isCreating || isJoining}
            className="w-full border-brutal-lg bg-sasta-accent text-sasta-black px-8 py-4 font-zero font-bold text-xl shadow-brutal-lg hover:translate-x-1 hover:translate-y-1 hover:shadow-brutal-sm transition-all disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? '> CREATING...' : '> CREATE GAME'}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-4 border-sasta-black"></div>
            </div>
            <div className="relative flex justify-center">
              <span className="px-4 bg-sasta-white font-zero font-bold">OR</span>
            </div>
          </div>

          <div className="border-brutal-lg bg-sasta-white p-6 shadow-brutal-lg">
            <label className="font-zero font-bold text-sm mb-2 block">GAME CODE:</label>
            <input
              type="text"
              value={gameCode}
              onChange={(e) => setGameCode(e.target.value)}
              placeholder="ENTER CODE..."
              className="w-full p-4 border-brutal-sm bg-sasta-white font-zero text-lg placeholder:text-sasta-black/40 mb-4"
              onKeyPress={(e) => {
                if (e.key === 'Enter' && gameCode.trim()) handleJoinGame()
              }}
            />
            <button
              onClick={handleJoinGame}
              disabled={isJoining || isCreating || !gameCode.trim()}
              className="w-full border-brutal-sm bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isJoining ? '> JOINING...' : '> JOIN GAME'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
