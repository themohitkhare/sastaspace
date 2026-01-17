import { useEffect, useState } from 'react'
import { BrowserRouter, Routes, Route, Navigate, useParams } from 'react-router-dom'
import { useGameStore } from './store/useGameStore'
import { apiClient } from './api/apiClient'
import HomePage from './pages/HomePage'
import LobbyPage from './pages/LobbyPage'
import GamePage from './pages/GamePage'

function ProtectedRoute({ children }) {
  const { gameId: urlGameId } = useParams()
  const storeGameId = useGameStore((s) => s.gameId)
  const setGameId = useGameStore((s) => s.setGameId)
  
  // Use gameId from URL if available, otherwise fall back to store
  const gameId = urlGameId || storeGameId
  
  // If URL has gameId but store doesn't, set it in store
  useEffect(() => {
    if (urlGameId && urlGameId !== storeGameId) {
      setGameId(urlGameId)
    }
  }, [urlGameId, storeGameId, setGameId])
  
  if (!gameId) {
    return <Navigate to="/" replace />
  }
  return children
}

function GameRoute() {
  const { gameId: urlGameId } = useParams()
  const storeGameId = useGameStore((s) => s.gameId)
  const setGameId = useGameStore((s) => s.setGameId)
  const game = useGameStore((s) => s.game)
  const setGame = useGameStore((s) => s.setGame)
  const reset = useGameStore((s) => s.reset)
  const [isRestoring, setIsRestoring] = useState(false)
  const [restoreError, setRestoreError] = useState(null)

  // Use gameId from URL if available, otherwise fall back to store
  const gameId = urlGameId || storeGameId

  // Set gameId in store from URL if needed
  useEffect(() => {
    if (urlGameId && urlGameId !== storeGameId) {
      setGameId(urlGameId)
    }
  }, [urlGameId, storeGameId, setGameId])

  const playerId = useGameStore((s) => s.playerId)
  const setPlayerId = useGameStore((s) => s.setPlayerId)

  useEffect(() => {
    if (gameId && !game && !isRestoring) {
      setIsRestoring(true)
      setRestoreError(null)
      
      apiClient.get(`/sastadice/games/${gameId}/state`)
        .then((res) => {
          const restoredGame = res.data.game
          setGame(restoredGame, res.data.version)
          
          // Validate that stored playerId belongs to this game
          // If playerId exists but player is not in the game, clear it (spectator mode)
          if (playerId) {
            const playerExists = restoredGame.players?.some((p) => p.id === playerId)
            if (!playerExists) {
              // PlayerId doesn't belong to this game - clear it to enable spectator mode
              setPlayerId(null)
            }
          }
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
  }, [gameId, game, isRestoring, setGame, reset, playerId, setPlayerId])

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
          path="/lobby/:gameId"
          element={
            <ProtectedRoute>
              <GameRoute />
            </ProtectedRoute>
          }
        />
        <Route
          path="/game/:gameId"
          element={
            <ProtectedRoute>
              <GameRoute />
            </ProtectedRoute>
          }
        />
        {/* Legacy routes for backwards compatibility - redirect to new format */}
        <Route
          path="/lobby"
          element={<Navigate to="/" replace />}
        />
        <Route
          path="/game"
          element={<Navigate to="/" replace />}
        />
      </Routes>
    </BrowserRouter>
  )
}

export default App
