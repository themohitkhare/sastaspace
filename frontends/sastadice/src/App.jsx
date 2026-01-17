import React from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { useGameStore } from './store/useGameStore'
import HomePage from './pages/HomePage'
import LobbyPage from './pages/LobbyPage'
import GamePage from './pages/GamePage'

/**
 * ProtectedRoute - Redirects to home if no gameId
 */
function ProtectedRoute({ children }) {
  const gameId = useGameStore((s) => s.gameId)
  if (!gameId) {
    return <Navigate to="/" replace />
  }
  return children
}

/**
 * GameRoute - Routes to lobby or game based on game status
 * The child pages (LobbyPage/GamePage) will handle polling
 */
function GameRoute() {
  const gameId = useGameStore((s) => s.gameId)
  const game = useGameStore((s) => s.game)
  
  // If no game state yet, show loading (will be loaded by child pages)
  if (!game) {
    return (
      <div className="min-h-screen bg-sasta-white p-8 flex items-center justify-center">
        <p className="font-zero text-2xl">Loading game...</p>
      </div>
    )
  }

  // Route to appropriate page based on game status
  if (game.status === 'LOBBY') {
    return <LobbyPage />
  }

  if (game.status === 'ACTIVE' || game.status === 'FINISHED') {
    return <GamePage />
  }

  return <Navigate to="/" replace />
}

/**
 * App - Main entry point for SastaDice
 */
function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
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
