import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiClient } from '../api/apiClient'
import { useGameStore } from '../store/useGameStore'

export default function HomePage() {
  const navigate = useNavigate()
  const setGameId = useGameStore((s) => s.setGameId)
  const setGame = useGameStore((s) => s.setGame)
  const [gameCode, setGameCode] = useState('')
  const [isCreating, setIsCreating] = useState(false)
  const [isJoining, setIsJoining] = useState(false)

  const handleCreateGame = async () => {
    setIsCreating(true)
    try {
      const res = await apiClient.post('/sastadice/games')
      const game = res.data
      setGameId(game.id)
      setGame(game, 0)
      navigate('/game')
    } catch (err) {
      console.error('Error creating game:', err)
      alert('Failed to create game. Please try again.')
    } finally {
      setIsCreating(false)
    }
  }

  const handleJoinGame = async () => {
    const cleanGameCode = gameCode.trim().replace(/\s+/g, '').toLowerCase()
    
    if (!cleanGameCode) {
      alert('Please enter a game code')
      return
    }

    setIsJoining(true)
    try {
      const res = await apiClient.get(`/sastadice/games/${cleanGameCode}`)
      const game = res.data
      setGameId(game.id)
      setGame(game, 0)
      navigate('/game')
    } catch (err) {
      console.error('Error joining game:', err)
      if (err.response?.status === 404) {
        alert(`Game not found. Please check the game code: ${gameCode.trim()}`)
      } else {
        alert('Failed to join game. Please try again.')
      }
    } finally {
      setIsJoining(false)
    }
  }

  return (
    <div className="min-h-screen bg-sasta-white p-8 flex flex-col items-center justify-center">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-6xl font-bold font-zero mb-4">SASTADICE</h1>
          <p className="text-xl font-zero mb-8">Roll the dice, embrace the chaos.</p>
        </div>

        <div className="space-y-6">
          <button
            onClick={handleCreateGame}
            disabled={isCreating || isJoining}
            className="w-full border-brutal-lg bg-sasta-black text-sasta-white px-8 py-4 font-zero font-bold shadow-brutal-lg hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isCreating ? 'CREATING...' : 'CREATE GAME'}
          </button>

          <div className="relative">
            <div className="absolute inset-0 flex items-center">
              <div className="w-full border-t-2 border-sasta-black"></div>
            </div>
            <div className="relative flex justify-center text-sm">
              <span className="px-4 bg-sasta-white font-zero">OR</span>
            </div>
          </div>

          <div className="space-y-4">
            <input
              type="text"
              value={gameCode}
              onChange={(e) => setGameCode(e.target.value.toUpperCase())}
              placeholder="ENTER GAME CODE"
              className="w-full p-4 border-brutal-lg font-zero text-center text-xl font-bold placeholder:opacity-50"
              onKeyPress={(e) => {
                if (e.key === 'Enter') {
                  handleJoinGame()
                }
              }}
            />
            <button
              onClick={handleJoinGame}
              disabled={isJoining || isCreating || !gameCode.trim()}
              className="w-full border-brutal-lg bg-sasta-accent text-sasta-black px-8 py-4 font-zero font-bold shadow-brutal-lg hover:bg-sasta-black hover:text-sasta-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isJoining ? 'JOINING...' : 'JOIN GAME'}
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
