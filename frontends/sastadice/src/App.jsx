import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useGameStore } from './store/useGameStore'
import { apiClient } from './api/apiClient'
import HomePage from './pages/HomePage'
import LobbyPage from './pages/LobbyPage'
import GamePage from './pages/GamePage'

function ProtectedRoute({ children }) {
  const gameId = useGameStore((s) => s.gameId)
  if (!gameId) {
    return <Navigate to="/" replace />
  }
  return children
}

function GameRoute() {
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)
  const setGame = useGameStore((s) => s.setGame)
  const reset = useGameStore((s) => s.reset)
  const [isRestoring, setIsRestoring] = useState(false)
  const [restoreError, setRestoreError] = useState(null)

  useEffect(() => {
    if (gameId && !game && !isRestoring) {
      setIsRestoring(true)
      setRestoreError(null)
      
      apiClient.get(`/sastadice/games/${gameId}/state`)
        .then((res) => {
          setGame(res.data.game, res.data.version)
        })
        .catch((err) => {
          if (err.response?.status === 404) {
            setRestoreError('Game not found or expired')
            reset()
          } else {
            setRestoreError('Failed to restore session')
          }
        })
        .finally(() => {
          setIsRestoring(false)
        })
    }
  }, [gameId, game, isRestoring, setGame, reset])

  if (isRestoring || (!game && gameId)) {
    return (
      <div className="min-h-screen bg-sasta-white flex items-center justify-center">
        <div className="text-center border-brutal-lg p-8 shadow-brutal-lg">
          <div className="w-8 h-8 border-4 border-sasta-black border-t-sasta-accent animate-spin mx-auto mb-4"></div>
          <p className="font-zero text-lg">RESTORING SESSION...</p>
        </div>
      </div>
    )
  }

  if (restoreError) {
    return (
      <div className="min-h-screen bg-sasta-white flex items-center justify-center">
        <div className="text-center border-brutal-lg p-8 shadow-brutal-lg">
          <p className="font-zero text-lg text-red-500 mb-4">{restoreError}</p>
          <a href="/" className="font-zero underline">GO HOME</a>
        </div>
      </div>
    )
  }

  if (!game) {
    return <Navigate to="/" replace />
  }

  if (game.status === 'LOBBY') {
    return <LobbyPage />
  }

  if (game.status === 'ACTIVE' || game.status === 'FINISHED') {
    return <GamePage />
  }

  return <Navigate to="/" replace />
}

function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route
          path="/lobby"
          element={
            <ProtectedRoute>
              <GameRoute />
            </ProtectedRoute>
          }
        />
        <Route
          path="/game"
          element={
            <ProtectedRoute>
              <GameRoute />
            </ProtectedRoute>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
