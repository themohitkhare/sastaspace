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
    myPlayer,
    onDdosActivate,
    onManageProperties,
    hasUpgradeableProperties,
    board,
    players,
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

            // On state desync, just show error and refresh game state
            if (errorText && errorText.includes('Cannot roll dice in current turn phase')) {
                // Game state desync - will be fixed by next poll
                setError('State sync issue - refreshing...')
                if (onActionComplete) await onActionComplete({})
                return
            }

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

    const errorBanner = error ? (
        <div className="text-center py-2 px-4 bg-red-500 text-white font-zero text-xs border-brutal-sm mb-2">
            {error}
        </div>
    ) : null

    if (turnPhase === 'PRE_ROLL') {
        const hasDdosBuff = myPlayer?.active_buff === 'DDOS'
        return (
            <div className="space-y-2">
                {errorBanner}
                {hasUpgradeableProperties && onManageProperties && (
                    <button
                        onClick={onManageProperties}
                        disabled={isLoading}
                        className="w-full py-2 px-4 bg-purple-500 text-white font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        🏠 MANAGE PROPERTIES
                    </button>
                )}
                {hasDdosBuff && onDdosActivate && (
                    <button
                        onClick={() => onDdosActivate(true)}
                        disabled={isLoading}
                        className="w-full py-2 px-4 bg-purple-600 text-white font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        💀 USE DDOS
                    </button>
                )}
                <button
                    onClick={() => performAction('ROLL_DICE')}
                    disabled={isLoading}
                    className="w-full py-4 px-8 bg-sasta-accent text-sasta-black font-zero font-bold text-xl border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
                >
                    {isLoading ? '🎲 ROLLING...' : <>🎲 ROLL DICE<span className="text-[8px] opacity-50 ml-1">[SPACE]</span></>}
                </button>
            </div>
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

    if (turnPhase === 'DECISION' && pendingDecision?.type === 'EVENT_FORCE_BUY') {
        const ownedByOthers = (board || []).filter(t => t.owner_id && t.owner_id !== playerId && t.type === 'PROPERTY')
        return (
            <div className="space-y-1">
                <div className="text-center font-zero text-[10px] font-bold bg-red-700 text-white py-1 px-1 border-brutal-sm">
                    ⚔️ HOSTILE TAKEOVER
                </div>
                <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                    {ownedByOthers.map((tile) => (
                        <button
                            key={tile.id}
                            onClick={() => performAction('EVENT_FORCE_BUY', { tile_id: tile.id })}
                            disabled={isLoading}
                            className="py-1 px-2 bg-red-600 text-white font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50 text-left flex justify-between"
                        >
                            <span>{tile.name.substring(0, 12)}</span>
                            <span>${Math.floor(tile.price * 1.5)}</span>
                        </button>
                    ))}
                    <button
                        onClick={() => performAction('PASS_PROPERTY')}
                        disabled={isLoading}
                        className="w-full py-1 px-2 bg-sasta-white text-sasta-black font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        SKIP
                    </button>
                </div>
            </div>
        )
    }

    if (turnPhase === 'DECISION' && pendingDecision?.type === 'EVENT_CLONE_UPGRADE') {
        const ownedByOthers = (board || []).filter(t => t.owner_id && t.owner_id !== playerId && t.type === 'PROPERTY' && t.upgrade_level > 0)
        const myProperties = (board || []).filter(t => t.owner_id === playerId && t.type === 'PROPERTY')
        
        return (
            <div className="space-y-1">
                <div className="text-center font-zero text-[10px] font-bold bg-cyan-600 text-white py-1 px-1 border-brutal-sm">
                    🍴 FORK REPO
                </div>
                <div className="text-[9px] font-data text-white mb-1 text-center">Clone upgrades</div>
                <div className="flex flex-col gap-1 max-h-32 overflow-y-auto">
                    {ownedByOthers.map((source) =>
                        myProperties.map((target) => (
                            <button
                                key={`${source.id}-${target.id}`}
                                onClick={() => performAction('EVENT_CLONE_UPGRADE', { source_tile_id: source.id, target_tile_id: target.id })}
                                disabled={isLoading}
                                className="py-1 px-1 bg-cyan-500 text-white font-zero text-[9px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50 text-left"
                            >
                                {source.name.substring(0, 8)} L{source.upgrade_level} → {target.name.substring(0, 8)}
                            </button>
                        ))
                    )}
                    <button
                        onClick={() => performAction('PASS_PROPERTY')}
                        disabled={isLoading}
                        className="w-full py-1 px-2 bg-sasta-white text-sasta-black font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        SKIP
                    </button>
                </div>
            </div>
        )
    }

    if (turnPhase === 'DECISION' && pendingDecision?.type === 'EVENT_FREE_LANDING') {
        const myProperties = (board || []).filter(t => t.owner_id === playerId && t.type === 'PROPERTY')
        return (
            <div className="space-y-1">
                <div className="text-center font-zero text-[10px] font-bold bg-green-600 text-white py-1 px-1 border-brutal-sm">
                    🔓 OPEN SOURCE
                </div>
                <div className="text-[9px] font-data text-white mb-1 text-center">Make property free for 1 round</div>
                <div className="flex flex-col gap-1 max-h-40 overflow-y-auto">
                    {myProperties.map((tile) => (
                        <button
                            key={tile.id}
                            onClick={() => performAction('EVENT_FREE_LANDING', { tile_id: tile.id })}
                            disabled={isLoading}
                            className="py-1 px-2 bg-green-500 text-white font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50 text-left"
                        >
                            {tile.name}
                        </button>
                    ))}
                    <button
                        onClick={() => performAction('PASS_PROPERTY')}
                        disabled={isLoading}
                        className="w-full py-1 px-2 bg-sasta-white text-sasta-black font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        SKIP
                    </button>
                </div>
            </div>
        )
    }

    if (turnPhase === 'DECISION' && pendingDecision?.type === 'MARKET') {
        const buffs = pendingDecision?.event_data?.buffs || []
        return (
            <div className="space-y-1">
                <div className="text-center font-zero text-[10px] font-bold bg-sasta-black text-sasta-accent py-1 px-1 border-brutal-sm">
                    BLACK MARKET
                </div>
                <div className="flex flex-col gap-1">
                    {buffs.map((buff) => (
                        <button
                            key={buff.id}
                            onClick={() => performAction('BUY_BUFF', { buff_id: buff.id })}
                            disabled={isLoading}
                            className="py-1 px-2 bg-sasta-accent text-sasta-black font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50 text-left flex justify-between"
                        >
                            <span>{buff.name.split(' ')[0]}</span>
                            <span>${buff.cost}</span>
                        </button>
                    ))}
                    <button
                        onClick={() => performAction('PASS_PROPERTY')}
                        disabled={isLoading}
                        className="w-full py-1 px-2 bg-sasta-white text-sasta-black font-zero text-[10px] font-bold border-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        LEAVE [N]
                    </button>
                </div>
            </div>
        )
    }

    if (turnPhase === 'POST_TURN') {
        const hasDdosBuff = myPlayer?.active_buff === 'DDOS'
        return (
            <div className="space-y-2">
                {errorBanner}
                {hasUpgradeableProperties && onManageProperties && (
                    <button
                        onClick={onManageProperties}
                        disabled={isLoading}
                        className="w-full py-2 px-4 bg-purple-500 text-white font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        🏠 MANAGE PROPERTIES
                    </button>
                )}
                {hasDdosBuff && onDdosActivate && (
                    <button
                        onClick={() => onDdosActivate(true)}
                        disabled={isLoading}
                        className="w-full py-2 px-4 bg-purple-600 text-white font-zero font-bold text-sm border-brutal-sm shadow-brutal-sm hover:translate-x-0.5 hover:translate-y-0.5 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        💀 USE DDOS
                    </button>
                )}
                <button
                    onClick={() => performAction('END_TURN')}
                    disabled={isLoading}
                    className="w-full py-4 px-8 bg-sasta-black text-sasta-accent font-zero font-bold text-xl border-brutal-sm shadow-brutal-sm hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
                >
                    {isLoading ? '⏳ ENDING...' : <>→ END TURN<span className="text-[8px] opacity-50 ml-1">[SPACE]</span></>}
                </button>
            </div>
        )
    }

    return null
}
