import React from 'react'
import { TILE_TYPE_COLORS } from './TileComponent'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'

export default function PropertyDetailsModal({ tile, onClose, onRefresh }) {
    if (!tile) return null

    const gameId = useGameStore(s => s.gameId)
    const game = useGameStore(s => s.game)
    const playerId = useGameStore(s => s.playerId)
    const myPlayer = game?.players?.find(p => p.id === playerId)

    const owner = game?.players?.find(p => p.id === tile.owner_id)
    const isOwner = owner?.id === playerId
    const isUnowned = !tile.owner_id
    const isProeprty = tile.type === 'PROPERTY'

    // Check upgrade eligibility
    const canUpgrade = isOwner && tile.upgrade_level < 2

    // Check full set ownership
    const colorTiles = game?.board?.filter(t => t.type === 'PROPERTY' && t.color === tile.color) || []
    const ownsFullSet = colorTiles.length > 0 && colorTiles.every(t => t.owner_id === playerId)

    // Upgrade cost
    // Level 0 -> 1: Base Price
    // Level 1 -> 2: Base Price * 2
    const upgradeCost = tile.price * (tile.upgrade_level === 1 ? 2 : 1)
    const canAfford = myPlayer?.cash >= upgradeCost

    const levelName = tile.upgrade_level === 0 ? 'BASIC' : tile.upgrade_level === 1 ? 'SCRIPT KIDDIE' : '1337 HAXXOR'
    const nextLevelName = tile.upgrade_level === 0 ? 'SCRIPT KIDDIE' : '1337 HAXXOR'

    const handleUpgrade = async () => {
        try {
            await apiClient.post(`/sastadice/games/${gameId}/action`, {
                type: 'UPGRADE',
                player_id: playerId,
                payload: { tile_id: tile.id }
            })
            onRefresh && onRefresh()
            onClose && onClose()
        } catch (err) {
            alert(err.response?.data?.message || 'Upgrade failed')
        }
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
            <div className="bg-sasta-white border-brutal-lg shadow-brutal-lg max-w-sm w-full p-0 overflow-hidden text-left" onClick={e => e.stopPropagation()}>
                {/* Header */}
                <div
                    className="p-4 text-center font-zero font-bold text-xl text-sasta-black border-b-2 border-sasta-black relative"
                    style={{ backgroundColor: TILE_TYPE_COLORS[tile.type] || '#FFFFFF' }}
                >
                    {tile.name.toUpperCase()}
                    <button onClick={onClose} className="absolute top-2 right-2 text-xs bg-black text-white px-2 py-1">X</button>
                </div>

                <div className="p-4 font-data space-y-3">
                    {/* Status */}
                    <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                        <span className="text-zinc-500 text-xs">TYPE</span>
                        <span className="font-bold text-sm">{tile.type}</span>
                    </div>

                    {isProeprty && (
                        <>
                            <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                                <span className="text-zinc-500 text-xs">OWNER</span>
                                <span className="font-bold flex items-center gap-2">
                                    {owner ? (
                                        <>
                                            <div className="w-3 h-3 rounded-full border border-black" style={{ backgroundColor: owner.color }}></div>
                                            {owner.name.toUpperCase()}
                                        </>
                                    ) : (
                                        <span className="text-zinc-400">UNOWNED</span>
                                    )}
                                </span>
                            </div>

                            <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                                <span className="text-zinc-500 text-xs">RENT</span>
                                <span className="font-bold text-lg">${tile.rent || 0}</span>
                            </div>

                            <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                                <span className="text-zinc-500 text-xs">LEVEL</span>
                                <span className="font-bold text-sasta-accent bg-sasta-black px-2 text-xs">{levelName} {tile.upgrade_level > 0 && '⚡'}</span>
                            </div>

                            {/* Upgrade UI */}
                            {isOwner && (
                                <div className="mt-4 pt-2 border-t-2 border-sasta-black">
                                    {tile.upgrade_level < 2 ? (
                                        <div>
                                            <div className="flex justify-between items-center mb-2">
                                                <span className="text-xs font-bold">UPGRADE TO {nextLevelName}</span>
                                                <span className="text-sm font-bold">${upgradeCost}</span>
                                            </div>

                                            {!ownsFullSet ? (
                                                <p className="text-[10px] text-red-500 text-center bg-red-50 p-1 mb-2">
                                                    MUST OWN ALL {tile.color} PROPERTIES
                                                </p>
                                            ) : (
                                                <button
                                                    onClick={handleUpgrade}
                                                    disabled={!canAfford}
                                                    className={`w-full py-2 border-brutal-sm font-bold text-sm transition-transform active:scale-95 ${canAfford
                                                            ? 'bg-sasta-accent text-sasta-black hover:bg-white'
                                                            : 'bg-gray-200 text-gray-400 cursor-not-allowed'
                                                        }`}
                                                >
                                                    {canAfford ? 'UPGRADE NOW' : 'INSUFFICIENT FUNDS'}
                                                </button>
                                            )}
                                        </div>
                                    ) : (
                                        <div className="text-center text-green-600 font-bold text-sm py-2 bg-green-50 border border-green-200">
                                            ★ MAX LEVEL REACHED ★
                                        </div>
                                    )}
                                </div>
                            )}
                        </>
                    )}

                    {!isProeprty && (
                        <div className="bg-gray-50 p-2 text-xs text-center border overflow-auto max-h-40">
                            {tile.description || JSON.stringify(tile.effect_config) || 'No details'}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}
