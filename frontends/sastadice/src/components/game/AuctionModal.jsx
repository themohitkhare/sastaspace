import { useEffect, useState, useRef } from 'react'

export default function AuctionModal({ auctionState, tiles, players, playerId, onBid, onExpire, game, onClose }) {
    const [timeLeft, setTimeLeft] = useState(0)
    const [stuckTimer, setStuckTimer] = useState(0)
    const [error, setError] = useState(null)
    const resolveAttempted = useRef(false)

    useEffect(() => {
        resolveAttempted.current = false
        setStuckTimer(0)
        setError(null)
    }, [auctionState?.property_id])

    // Timer effect with stuck detection
    useEffect(() => {
        const timer = setInterval(() => {
            if (!auctionState) return

            const remaining = Math.max(0, auctionState.end_time - Date.now() / 1000)
            setTimeLeft(remaining)

            // Track how long we've been stuck at 0
            if (remaining <= 0) {
                setStuckTimer(prev => prev + 0.05)
            } else {
                setStuckTimer(0)
            }

            // Force resolve on first hit of 0
            if (remaining <= 0 && !resolveAttempted.current && onExpire) {
                resolveAttempted.current = true
                onExpire()
            }
        }, 50)
        return () => clearInterval(timer)
    }, [auctionState, onExpire])

    // Close modal when auction phase ends (server-driven)
    useEffect(() => {
        if (game?.turn_phase !== 'AUCTION' || !game?.auction_state) {
            onClose?.()
        }
    }, [game?.turn_phase, game?.auction_state, onClose])

    if (!auctionState) return null

    const property = tiles.find(t => t.id === auctionState.property_id)
    const highestBidder = players.find(p => p.id === auctionState.highest_bidder_id)
    const currentBid = auctionState.highest_bid

    // Fixed bid calculation: start from max(currentBid, basePrice)
    const startPrice = Math.max(currentBid, property?.price || 0)

    const handleBid = (amount) => {
        setError(null)
        onBid(amount)
    }

    const handleManualSync = () => {
        if (onExpire) onExpire()
    }

    const quickBidIncrements = [10, 50, 100]
    const isHighestBidder = highestBidder?.id === playerId
    const isPanicMode = timeLeft < 5
    const showSyncButton = timeLeft <= 0 && stuckTimer > 1

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-md animate-fade-in">
            <div className={`w-full max-w-md bg-sasta-black border-[4px] ${isPanicMode ? 'border-red-600 animate-pulse' : 'border-red-500'} shadow-[0_0_50px_rgba(255,0,0,0.5)] p-6 relative overflow-hidden transition-all duration-75`}>

                {/* Header */}
                <div className="text-center mb-4 relative z-10">
                    <h2 className={`font-zero text-3xl font-bold text-red-500 inline-block px-3 py-1 mb-2 transform bg-black border-2 border-red-500 ${isPanicMode ? 'animate-ping' : ''}`}>
                        ⚠️ BIDDING WAR ⚠️
                    </h2>
                </div>

                {/* Property Card */}
                <div className="flex justify-center mb-6 relative z-10">
                    <div className="w-48 border-4 border-white bg-white p-2 shadow-[10px_10px_0_rgba(255,0,0,1)] transform -rotate-2 hover:rotate-0 transition-transform duration-300 scale-110">
                        <div
                            className="h-16 border-b-4 border-black mb-2 flex items-center justify-center font-zero font-black text-xl text-center leading-none"
                            style={{ backgroundColor: property?.color || '#ccc' }}
                        >
                            <span className="drop-shadow-md text-white px-1 uppercase tracking-tighter" style={{ textShadow: '2px 2px 0 #000' }}>
                                {property?.name}
                            </span>
                        </div>
                        <div className="text-center font-mono font-bold text-sm mb-1 uppercase tracking-widest">
                            Base: ${property?.price}
                        </div>
                    </div>
                </div>

                {/* Winner Badge */}
                <div className="text-center mb-2 relative z-10">
                    {isHighestBidder ? (
                        <div className="inline-block px-4 py-1 bg-green-500 text-black font-mono font-bold text-xs uppercase tracking-widest border-2 border-green-400">
                            [ YOU ARE WINNING ]
                        </div>
                    ) : highestBidder ? (
                        <div className="inline-block px-4 py-1 bg-red-600 text-white font-mono font-bold text-xs uppercase tracking-widest border-2 border-red-500">
                            [ WINNING: {highestBidder.name} ]
                        </div>
                    ) : (
                        <div className="h-6"></div>
                    )}
                </div>

                {/* Price Display */}
                <div className="text-center mb-6 space-y-2 relative z-10">
                    <div className="font-mono text-xs text-red-500 tracking-[0.3em] font-bold">CURRENT PRICE</div>
                    {currentBid > 0 ? (
                        <div className="font-mono text-7xl font-black text-[#00ff2b] drop-shadow-[4px_4px_0_rgba(0,0,0,1)] tracking-tighter leading-none">
                            ${currentBid}
                        </div>
                    ) : (
                        <div className="font-mono text-5xl font-black text-yellow-500 drop-shadow-[4px_4px_0_rgba(0,0,0,1)] tracking-tighter leading-none">
                            START: ${property?.price}
                        </div>
                    )}
                </div>

                {/* Timer */}
                <div className="text-center mb-6 relative z-10">
                    <div className={`font-mono font-black text-6xl transition-colors duration-100 ${timeLeft < 5 ? 'text-red-500 animate-shake' : 'text-white'}`}>
                        {timeLeft.toFixed(1)}s
                    </div>
                </div>

                {/* Error Toast */}
                {error && (
                    <div className="mb-4 relative z-10">
                        <div className="bg-red-500 text-white px-4 py-2 text-center font-mono font-bold text-sm animate-pulse">
                            {error}
                        </div>
                    </div>
                )}

                {/* Manual Sync Button */}
                {showSyncButton && (
                    <div className="mb-4 relative z-10">
                        <button
                            onClick={handleManualSync}
                            className="w-full py-2 px-4 bg-yellow-500 text-black font-mono font-bold text-sm border-2 border-yellow-400 hover:bg-yellow-400 transition-colors"
                        >
                            ⚠️ SYNC NOW
                        </button>
                    </div>
                )}

                {/* Bid Buttons */}
                {playerId && (
                <div className="grid grid-cols-3 gap-3 relative z-10">
                    {quickBidIncrements.map((inc, idx) => {
                        const totalBid = startPrice + inc
                        const isHighValue = inc === 100
                        return (
                            <button
                                key={inc}
                                onClick={() => handleBid(totalBid)}
                                disabled={isHighestBidder}
                                className={`
                                    py-4 px-2 border-2
                                    ${isHighValue
                                        ? 'bg-green-500 text-black border-green-400 hover:bg-green-400'
                                        : 'bg-[#111] text-white border-white hover:bg-[#222]'
                                    }
                                    active:scale-95
                                    font-mono font-bold text-sm
                                    transition-all duration-75 uppercase
                                    disabled:opacity-30 disabled:cursor-not-allowed
                                    hover:shadow-[0_0_15px_rgba(255,255,255,0.5)]
                                    flex flex-col items-center justify-center gap-1
                                `}
                            >
                                <span className={`text-xs ${isHighValue ? 'text-green-900' : 'text-green-400'}`}>+${inc}</span>
                                <span className="text-lg">BID ${totalBid}</span>
                            </button>
                        )
                    })}
                </div>
                )}
                {!playerId && (
                    <div className="text-center text-sm font-zero text-gray-500 py-2">SPECTATOR VIEW</div>
                )}
            </div>
        </div>
    )
}
