import React, { useState } from 'react'
import { TILE_TYPE_COLORS } from './TileComponent'
import { apiClient } from '../../api/apiClient'
import { useGameStore } from '../../store/useGameStore'
import { useToast } from '../../hooks/useToast'
import ToastContainer from '../ToastContainer'

export default function PropertyDetailsModal({ tile, onClose, onRefresh }) {
    const { toasts, showToast, dismissToast } = useToast()

    if (!tile) return null

    const gameId = useGameStore(s => s.gameId)
    const game = useGameStore(s => s.game)
    const playerId = useGameStore(s => s.playerId)
    const myPlayer = game?.players?.find(p => p.id === playerId)

    const owner = game?.players?.find(p => p.id === tile.owner_id)
    const isOwner = owner?.id === playerId
    const isUnowned = !tile.owner_id
    const isProperty = tile.type === 'PROPERTY'

    const canUpgrade = isOwner && tile.upgrade_level < 2

    const colorTiles = game?.board?.filter(t => t.type === 'PROPERTY' && t.color === tile.color) || []
    const ownsFullSet = colorTiles.length > 0 && colorTiles.every(t => t.owner_id === playerId)

    const ownerOwnsFullSet = owner && colorTiles.length > 0 && colorTiles.every(t => t.owner_id === owner.id)

    const calculateDisplayRent = () => {
        let rent = tile.rent || 0
        if (ownerOwnsFullSet) rent *= 2
        if (tile.upgrade_level === 1) rent = Math.floor(rent * 1.5)
        else if (tile.upgrade_level === 2) rent = Math.floor(rent * 3.0)
        return rent
    }
    const displayRent = calculateDisplayRent()
    const hasBonus = displayRent !== (tile.rent || 0)

    const upgradeCost = tile.price * (tile.upgrade_level === 1 ? 2 : 1)
    const canAfford = myPlayer?.cash >= upgradeCost

    const levelName = tile.upgrade_level === 0 ? 'BASIC' : tile.upgrade_level === 1 ? 'SCRIPT KIDDIE' : '1337 HAXXOR'
    const nextLevelName = tile.upgrade_level === 0 ? 'SCRIPT KIDDIE' : '1337 HAXXOR'

    const handleUpgrade = async () => {
        try {
            await apiClient.post(`/sastadice/games/${gameId}/action?player_id=${playerId}`, {
                type: 'UPGRADE',
                payload: { tile_id: tile.id }
            })
            onRefresh && onRefresh()
            onClose && onClose()
        } catch (err) {
            showToast(err.response?.data?.message || 'Upgrade failed')
        }
    }

    const downgradeRefund = tile.upgrade_level === 2
        ? tile.price
        : Math.floor(tile.price / 2)

    const handleDowngrade = async () => {
        if (!confirm(`Sell upgrade for $${downgradeRefund}?`)) return
        try {
            await apiClient.post(`/sastadice/games/${gameId}/action?player_id=${playerId}`, {
                type: 'DOWNGRADE',
                payload: { tile_id: tile.id }
            })
            onRefresh && onRefresh()
            onClose && onClose()
        } catch (err) {
            showToast(err.response?.data?.message || 'Downgrade failed')
        }
    }

    return (
        <>
        <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
            <div className="bg-sasta-white border-brutal-lg shadow-brutal-lg max-w-sm w-full p-0 overflow-hidden text-left" onClick={e => e.stopPropagation()}>
                <div
                    className="p-4 text-center font-zero font-bold text-xl text-sasta-black border-b-2 border-sasta-black relative"
                    style={{ backgroundColor: TILE_TYPE_COLORS[tile.type] || '#FFFFFF' }}
                >
                    {tile.name.toUpperCase()}
                    <button onClick={onClose} className="absolute top-2 right-2 text-xs bg-black text-white px-2 py-1">X</button>
                </div>

                <div className="p-4 font-data space-y-3">
                    <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                        <span className="text-zinc-500 text-xs">TYPE</span>
                        <span className="font-bold text-sm">{tile.type}</span>
                    </div>

                    {isProperty && (
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
                                <span className="font-bold text-lg">
                                    ${displayRent}
                                    {hasBonus && (
                                        <span className="text-xs text-green-600 ml-1">
                                            (base: ${tile.rent})
                                        </span>
                                    )}
                                </span>
                            </div>

                            <div className="flex justify-between items-center border-b border-gray-200 pb-2">
                                <span className="text-zinc-500 text-xs">LEVEL</span>
                                <span className="font-bold text-sasta-accent bg-sasta-black px-2 text-xs">{levelName} {tile.upgrade_level > 0 && '⚡'}</span>
                            </div>

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

                                    {tile.upgrade_level > 0 && (
                                        <button
                                            onClick={handleDowngrade}
                                            className="w-full py-2 mt-2 border-brutal-sm font-bold text-sm bg-red-100 text-red-700 hover:bg-red-200 transition-colors"
                                        >
                                            💸 SELL UPGRADE (+${downgradeRefund})
                                        </button>
                                    )}
                                </div>
                            )}
                        </>
                    )}

                    {!isProperty && (
                        <div className="bg-gray-50 p-2 text-xs text-center border overflow-auto max-h-40">
                            {tile.description || JSON.stringify(tile.effect_config) || 'No details'}
                        </div>
                    )}
                </div>
            </div>
        </div>
        </>
    )
}
