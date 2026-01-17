/**
 * DiceRoller - Component for rolling dice
 */
import React, { useState } from 'react'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'

export default function DiceRoller() {
  const [isRolling, setIsRolling] = useState(false)
  const gameId = useGameStore((s) => s.gameId)
  const playerId = useGameStore((s) => s.playerId)
  const isMyTurn = useGameStore((s) => s.isMyTurn())

  const handleRoll = async () => {
    if (!gameId || !playerId || !isMyTurn || isRolling) return

    setIsRolling(true)

    try {
      await apiClient.post(
        `/sastadice/games/${gameId}/action?player_id=${playerId}`,
        {
          type: 'ROLL_DICE',
          payload: {},
        }
      )
    } catch (err) {
      console.error('Error rolling dice:', err)
    } finally {
      setIsRolling(false)
    }
  }

  if (!isMyTurn) {
    return (
      <div className="p-4 border-brutal bg-gray-100">
        <p className="font-zero font-bold">Waiting for your turn...</p>
      </div>
    )
  }

  return (
    <div className="p-4 border-brutal bg-sasta-accent">
      <button
        onClick={handleRoll}
        disabled={isRolling}
        className="border-brutal-sm bg-sasta-black text-sasta-white px-6 py-3 font-zero font-bold shadow-brutal-sm hover:bg-sasta-accent hover:text-sasta-black transition-colors disabled:opacity-50"
      >
        {isRolling ? 'ROLLING...' : 'ROLL DICE'}
      </button>
    </div>
  )
}
