import { useState, useEffect } from 'react'
import { apiClient } from '../../api/apiClient'

export default function CenterActionButton({
    gameId,
    playerId,
    turnPhase,
    pendingDecision,
    isMyTurn,
    isCpuTurn,
    onActionComplete,
}) {
    const [isLoading, setIsLoading] = useState(false)
    const [error, setError] = useState(null)

    const performAction = async (actionType, payload = {}) => {
        if (!gameId || !playerId) return

        if (actionType === 'ROLL_DICE' && turnPhase !== 'PRE_ROLL') {
            if (onActionComplete) await onActionComplete({})
            return
        }

        if (actionType === 'END_TURN' && turnPhase !== 'POST_TURN') {
            if (onActionComplete) await onActionComplete({})
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
                setError(response.data.message || 'Action failed')
            }
            if (onActionComplete) await onActionComplete(response.data)
        } catch (err) {
            const errorDetail = err.response?.data?.detail
            const errorText = Array.isArray(errorDetail)
                ? errorDetail.map((e) => e.msg).join(', ')
                : typeof errorDetail === 'string'
                    ? errorDetail
                    : err.message
            setError(errorText)
            if (onActionComplete) await onActionComplete({})
        } finally {
            setIsLoading(false)
        }
    }

    useEffect(() => {
        if (!playerId || isLoading) return

        const handleKeyPress = (e) => {
            const target = e.target
            if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return

            if (e.key === ' ' || e.key === 'Spacebar') {
                e.preventDefault()
                if (turnPhase === 'PRE_ROLL' && isMyTurn) performAction('ROLL_DICE')
                else if (turnPhase === 'POST_TURN' && isMyTurn) performAction('END_TURN')
            }
            if ((e.key === 'y' || e.key === 'Y') && turnPhase === 'DECISION' && isMyTurn) {
                e.preventDefault()
                performAction('BUY_PROPERTY')
            }
            if ((e.key === 'n' || e.key === 'N') && turnPhase === 'DECISION' && isMyTurn) {
                e.preventDefault()
                performAction('PASS_PROPERTY')
            }
        }

        window.addEventListener('keydown', handleKeyPress)
        return () => window.removeEventListener('keydown', handleKeyPress)
    }, [playerId, isLoading, turnPhase, isMyTurn])

    if (!playerId) {
        return (
            <div className="text-center py-2 px-4 bg-blue-500/20 border-2 border-blue-400 font-zero text-sm">
                👁️ SPECTATOR MODE
            </div>
        )
    }

    if (isCpuTurn) {
        return (
            <div className="text-center py-3 px-6 bg-sasta-black font-zero text-sasta-accent animate-pulse border-brutal-sm">
                🤖 CPU THINKING...
            </div>
        )
    }

    if (!isMyTurn) {
        return (
            <div className="text-center py-3 px-6 bg-sasta-black/10 font-zero text-sm border-brutal-sm">
                WAITING FOR OTHER PLAYER...
            </div>
        )
    }

    if (error) {
        return (
            <div className="text-center py-2 px-4 bg-red-500 text-white font-zero text-xs border-brutal-sm">
                {error}
            </div>
        )
    }

    if (turnPhase === 'PRE_ROLL') {
        return (
            <button
                onClick={() => performAction('ROLL_DICE')}
                disabled={isLoading}
                className="w-full py-4 px-8 bg-sasta-accent text-sasta-black font-zero font-bold text-xl border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
            >
                {isLoading ? '🎲 ROLLING...' : '🎲 ROLL DICE'}
            </button>
        )
    }

    if (turnPhase === 'DECISION' && pendingDecision?.type === 'BUY') {
        return (
            <div className="space-y-2">
                <div className="text-center font-zero text-sm font-bold bg-sasta-black text-sasta-accent py-2 px-4 border-brutal-sm">
                    BUY FOR ${pendingDecision?.price || 0}?
                </div>
                <div className="flex gap-2">
                    <button
                        onClick={() => performAction('BUY_PROPERTY')}
                        disabled={isLoading}
                        className="flex-1 py-3 px-4 bg-sasta-accent text-sasta-black font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        ✓ BUY [Y]
                    </button>
                    <button
                        onClick={() => performAction('PASS_PROPERTY')}
                        disabled={isLoading}
                        className="flex-1 py-3 px-4 bg-sasta-white text-sasta-black font-zero font-bold border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        ✗ PASS [N]
                    </button>
                </div>
            </div>
        )
    }

    if (turnPhase === 'POST_TURN') {
        return (
            <button
                onClick={() => performAction('END_TURN')}
                disabled={isLoading}
                className="w-full py-4 px-8 bg-sasta-black text-sasta-accent font-zero font-bold text-xl border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
            >
                {isLoading ? '⏳ ENDING...' : '→ END TURN'}
            </button>
        )
    }

    return null
}
