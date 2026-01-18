import { useState, useEffect } from 'react'
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

    if (actionType === 'ROLL_DICE' && turnPhase !== 'PRE_ROLL') {
      setError('Cannot roll dice - not in PRE_ROLL phase. Refreshing game state...')
      if (onActionComplete) {
        await onActionComplete({})
        setTimeout(() => setError(null), 1000)
      }
      return
    }
    
    if (actionType === 'END_TURN' && turnPhase !== 'POST_TURN') {
      setError(`Cannot end turn - currently in ${turnPhase} phase. Refreshing game state...`)
      if (onActionComplete) {
        await onActionComplete({})
        setTimeout(() => setError(null), 1000)
      }
      return
    }

    setIsLoading(true)
    setError(null)

    try {
      const response = await apiClient.post(
        `/sastadice/games/${gameId}/action?player_id=${playerId}`,
        { type: actionType, payload }
      )

      if (!response.data.success) {
        const errorMsg = response.data.message || 'Action failed'
        setError(errorMsg)
        
        if (errorMsg.includes('turn phase') || errorMsg.includes('Cannot roll dice')) {
          if (onActionComplete) {
            await onActionComplete(response.data)
            setTimeout(() => setError(null), 1000)
          }
        }
      } else {
        setError(null)
        if (onActionComplete) {
          await onActionComplete(response.data)
        }
      }
    } catch (err) {
      const errorDetail = err.response?.data?.detail
      const errorText = Array.isArray(errorDetail)
        ? errorDetail.map((e) => e.msg).join(', ')
        : typeof errorDetail === 'string'
          ? errorDetail
          : err.message
      setError(errorText)
      
      if (errorText.includes('turn phase') || errorText.includes('Cannot roll dice')) {
        if (onActionComplete) {
          await onActionComplete({})
          setTimeout(() => setError(null), 1000)
        }
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleRollDice = () => performAction('ROLL_DICE')
  const handleBuyProperty = () => performAction('BUY_PROPERTY')
  const handlePassProperty = () => performAction('PASS_PROPERTY')
  const handleEndTurn = () => performAction('END_TURN')

  const showRollDice = turnPhase === 'PRE_ROLL' && isMyTurn
  const showDecision = turnPhase === 'DECISION' && isMyTurn && pendingDecision?.type === 'BUY'
  const showEndTurn = turnPhase === 'POST_TURN' && isMyTurn
  const showWaiting = !isMyTurn

  useEffect(() => {
    if (!playerId || isLoading) return

    const handleKeyPress = (e) => {
      // Don't trigger shortcuts if user is typing in an input, textarea, or contenteditable
      const target = e.target
      if (
        target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable
      ) {
        return
      }

      // Space bar: Roll dice (PRE_ROLL) or End turn (POST_TURN)
      if (e.key === ' ' || e.key === 'Spacebar') {
        e.preventDefault()
        if (showRollDice) {
          performAction('ROLL_DICE')
        } else if (showEndTurn) {
          performAction('END_TURN')
        }
      }

      // Y key: Buy property (DECISION phase)
      if (e.key === 'y' || e.key === 'Y') {
        e.preventDefault()
        if (showDecision) {
          performAction('BUY_PROPERTY')
        }
      }

      // N key: Pass property (DECISION phase)
      if (e.key === 'n' || e.key === 'N') {
        e.preventDefault()
        if (showDecision) {
          performAction('PASS_PROPERTY')
        }
      }
    }

    window.addEventListener('keydown', handleKeyPress)
    return () => {
      window.removeEventListener('keydown', handleKeyPress)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [playerId, isLoading, showRollDice, showEndTurn, showDecision])

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

      {/* Container with smooth transitions - always renders to prevent layout shifts */}
      {/* Min-height set to accommodate the tallest content (decision panel ~120px) */}
      <div className="relative min-h-[120px]">
        {/* Roll Dice Button */}
        <div
          className={`transition-opacity duration-200 ease-in-out ${
            showRollDice
              ? 'opacity-100 pointer-events-auto relative'
              : 'opacity-0 pointer-events-none absolute inset-0'
          }`}
        >
          <button
            onClick={handleRollDice}
            disabled={isLoading || !showRollDice}
            className="w-full py-3 px-4 bg-sasta-accent text-sasta-black font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
          >
            {isLoading ? '> ROLLING...' : '> ROLL DICE [SPACE]'}
          </button>
        </div>

        {/* Decision Panel */}
        <div
          className={`transition-opacity duration-200 ease-in-out ${
            showDecision
              ? 'opacity-100 pointer-events-auto relative'
              : 'opacity-0 pointer-events-none absolute inset-0'
          }`}
        >
          <div className="space-y-2">
            <div className="text-center font-zero text-xs font-bold bg-sasta-black text-sasta-accent p-2">
              BUY FOR ${pendingDecision?.price || 0}?
            </div>
            <div className="flex gap-2">
              <button
                onClick={handleBuyProperty}
                disabled={isLoading || !showDecision}
                className="flex-1 py-2 px-3 bg-sasta-accent text-sasta-black font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
              >
                {isLoading ? '...' : `BUY $${pendingDecision?.price || 0} [Y]`}
              </button>
              <button
                onClick={handlePassProperty}
                disabled={isLoading || !showDecision}
                className="flex-1 py-2 px-3 bg-sasta-white text-sasta-black font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
              >
                {isLoading ? '...' : 'PASS [N]'}
              </button>
            </div>
          </div>
        </div>

        {/* End Turn Button */}
        <div
          className={`transition-opacity duration-200 ease-in-out ${
            showEndTurn
              ? 'opacity-100 pointer-events-auto relative'
              : 'opacity-0 pointer-events-none absolute inset-0'
          }`}
        >
          <button
            onClick={handleEndTurn}
            disabled={isLoading || !showEndTurn}
            className="w-full py-3 px-4 bg-sasta-black text-sasta-accent font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
          >
            {isLoading ? '> ENDING...' : '> END TURN [SPACE]'}
          </button>
        </div>

        {/* Waiting Message - for players waiting their turn */}
        <div
          className={`transition-opacity duration-200 ease-in-out ${
            showWaiting && playerId
              ? 'opacity-100 pointer-events-auto relative'
              : 'opacity-0 pointer-events-none absolute inset-0'
          }`}
        >
          <div className="text-center py-3 px-4 bg-sasta-black/10 font-zero text-sm">
            WAITING FOR OTHER PLAYER...
          </div>
        </div>

        {/* Spectator Message - for non-players viewing the game */}
        {!playerId && (
          <div className="opacity-100 pointer-events-auto relative">
            <div className="text-center py-3 px-4 bg-blue-100 border-2 border-blue-400 font-zero text-sm">
              👁️ SPECTATOR MODE - VIEW ONLY
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
