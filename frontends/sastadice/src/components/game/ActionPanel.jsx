import { useState } from 'react'
import apiClient from '../../api/apiClient'

export default function ActionPanel({
  gameId,
  playerId,
  turnPhase,
  pendingDecision,
  isMyTurn,
  lastEventMessage,
  onActionComplete,
}) {
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState(null)

  const performAction = async (actionType, payload = {}) => {
    if (!gameId || !playerId) return

    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.post(`/sastadice/games/${gameId}/action`, {
        type: actionType,
        payload,
      })

      if (!response.data.success) {
        setError(response.data.message)
      }

      if (onActionComplete) {
        onActionComplete(response.data)
      }
    } catch (err) {
      setError(err.response?.data?.detail || err.message)
    } finally {
      setIsLoading(false)
    }
  }

  const handleRollDice = () => performAction('ROLL_DICE')
  const handleBuyProperty = () => performAction('BUY_PROPERTY')
  const handlePassProperty = () => performAction('PASS_PROPERTY')
  const handleEndTurn = () => performAction('END_TURN')

  return (
    <div className="action-panel w-full space-y-3">
      {lastEventMessage && (
        <div className="border-brutal-sm bg-sasta-accent p-3">
          <p className="font-zero text-xs text-sasta-black font-bold">{lastEventMessage}</p>
        </div>
      )}

      {error && (
        <div className="border-brutal-sm bg-red-500 text-sasta-white p-3">
          <p className="font-zero text-xs font-bold">{error}</p>
        </div>
      )}

      <div className="flex flex-col gap-2">
        {turnPhase === 'PRE_ROLL' && isMyTurn && (
          <button
            onClick={handleRollDice}
            disabled={isLoading}
            className="w-full py-3 px-4 bg-sasta-accent text-sasta-black font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
          >
            {isLoading ? '> ROLLING...' : '> ROLL DICE'}
          </button>
        )}

        {turnPhase === 'DECISION' && isMyTurn && pendingDecision?.type === 'BUY' && (
          <div className="space-y-2">
            <div className="text-center font-zero text-xs font-bold bg-sasta-black text-sasta-accent p-2">
              BUY FOR ${pendingDecision.price}?
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleBuyProperty}
                disabled={isLoading}
                className="flex-1 py-2 px-3 bg-sasta-accent text-sasta-black font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
              >
                {isLoading ? '...' : `BUY $${pendingDecision.price}`}
              </button>
              <button
                onClick={handlePassProperty}
                disabled={isLoading}
                className="flex-1 py-2 px-3 bg-sasta-white text-sasta-black font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
              >
                {isLoading ? '...' : 'PASS'}
              </button>
            </div>
          </div>
        )}

        {turnPhase === 'POST_TURN' && isMyTurn && (
          <button
            onClick={handleEndTurn}
            disabled={isLoading}
            className="w-full py-3 px-4 bg-sasta-black text-sasta-accent font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
          >
            {isLoading ? '> ENDING...' : '> END TURN'}
          </button>
        )}

        {!isMyTurn && (
          <div className="text-center py-3 px-4 bg-sasta-black/10 font-zero text-sm">
            WAITING FOR OTHER PLAYER...
          </div>
        )}
      </div>
    </div>
  )
}
