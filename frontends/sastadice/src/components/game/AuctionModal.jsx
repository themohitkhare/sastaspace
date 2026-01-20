import { useEffect, useState, useRef } from 'react'

export default function AuctionModal({ auctionState, tiles, players, playerId, onBid, onExpire }) {
    const [timeLeft, setTimeLeft] = useState(0)
    const [myBid, setMyBid] = useState('')
    const resolveAttempted = useRef(false)

    useEffect(() => {
        resolveAttempted.current = false
        setMyBid('')
    }, [auctionState?.property_id])

    useEffect(() => {
        const timer = setInterval(() => {
            if (!auctionState) return

            // Calculate remaining time
            // auctionState.end_time is Unix timestamp (seconds)
            // Date.now() is ms
            const remaining = Math.max(0, auctionState.end_time - Date.now() / 1000)
            setTimeLeft(remaining)

            if (remaining <= 0 && !resolveAttempted.current && onExpire) {
                resolveAttempted.current = true
                onExpire()
            }
        }, 100)
        return () => clearInterval(timer)
    }, [auctionState, onExpire])

    if (!auctionState) return null

    const property = tiles.find(t => t.id === auctionState.property_id)
    const highestBidder = players.find(p => p.id === auctionState.highest_bidder_id)
    const currentBid = auctionState.highest_bid
    // Min bid logic: current + increment. If 0, min is 10 (or start price? No, usually low start).
    // Schema says min_bid_increment = 10.
    const minBid = currentBid + auctionState.min_bid_increment

    const handleBid = (amount) => {
        onBid(amount)
        setMyBid('')
    }

    const quickBidAmounts = [
        minBid,
        minBid + 10,
        minBid + 50,
        minBid + 100
    ].filter(amt => amt > 0)

    const isHighestBidder = highestBidder?.id === playerId

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
            <div className="w-full max-w-md bg-sasta-white border-brutal-lg shadow-brutal-lg p-6 relative overflow-hidden">

                <div className="text-center mb-6">
                    <h2 className="font-zero text-2xl font-bold bg-sasta-black text-sasta-white inline-block px-3 py-1 mb-2 transform -rotate-1">
                        🔨 AUCTION TIME
                    </h2>
                    <div className="font-data text-sasta-black/60 text-sm">
                        BID TO WIN THIS PROPERTY
                    </div>
                </div>

                <div className="flex justify-center mb-6">
                    <div className="w-40 border-brutal-sm bg-white p-2 shadow-brutal-sm transform rotate-1">
                        <div
                            className="h-12 border-b-2 border-black mb-2 flex items-center justify-center font-zero font-bold text-center leading-none"
                            style={{ backgroundColor: property?.color || '#ccc' }}
                        >
                            <span className="drop-shadow-md text-white px-1" style={{ textShadow: '1px 1px 0 #000' }}>
                                {property?.name}
                            </span>
                        </div>
                        <div className="text-center font-data text-xs mb-2">
                            BASE PRICE: ${property?.price}
                        </div>
                    </div>
                </div>

                <div className="text-center mb-6 space-y-2">
                    <div className="font-data text-sm opacity-60">CURRENT HIGHEST BID</div>
                    <div className="font-zero text-4xl font-bold text-sasta-accent drop-shadow-[2px_2px_0_rgba(0,0,0,1)]">
                        ${currentBid}
                    </div>
                    {highestBidder ? (
                        <div className="font-data font-bold text-sm bg-black text-white inline-block px-2 py-0.5">
                            Held by: {highestBidder.name}
                        </div>
                    ) : (
                        <div className="font-data text-xs italic">No bids yet</div>
                    )}
                </div>

                <div className="w-full bg-sasta-black h-4 mb-6 relative border-brutal-sm">
                    <div
                        className="h-full transition-all duration-100 ease-linear"
                        style={{
                            width: `${Math.min(100, (timeLeft / 20) * 100)}%`,
                            backgroundColor: timeLeft < 3 ? '#FF0000' : timeLeft < 5 ? '#FF4444' : '#4ECDC4'
                        }}
                    />
                    <div className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-white font-mono">
                        {timeLeft.toFixed(1)}s
                    </div>
                </div>

                <div className="space-y-3">
                    <div className="grid grid-cols-2 gap-2">
                        {quickBidAmounts.map(amt => (
                            <button
                                key={amt}
                                onClick={() => handleBid(amt)}
                                disabled={isHighestBidder}
                                className="py-2 border-brutal-sm bg-white hover:bg-sasta-accent hover:translate-x-0.5 hover:translate-y-0.5 transition-all font-bold text-sm disabled:opacity-50 disabled:hover:translate-x-0 disabled:hover:translate-y-0 disabled:hover:bg-white"
                            >
                                BID ${amt}
                            </button>
                        ))}
                    </div>

                    <form
                        onSubmit={(e) => { e.preventDefault(); if (myBid) handleBid(parseInt(myBid)); }}
                        className="flex gap-2"
                    >
                        <input
                            type="number"
                            placeholder="Custom Amount..."
                            className="flex-1 border-brutal-sm p-2 font-data text-sm"
                            value={myBid}
                            onChange={(e) => setMyBid(e.target.value)}
                            min={minBid}
                        />
                        <button
                            type="submit"
                            disabled={isHighestBidder || !myBid}
                            className="px-4 border-brutal-sm bg-sasta-black text-white font-bold hover:bg-sasta-accent hover:text-black transition-colors disabled:opacity-50"
                        >
                            BID
                        </button>
                    </form>

                    {isHighestBidder && (
                        <div className="text-center font-data text-xs text-green-600 font-bold animate-bounce mt-2">
                            YOU ARE WINNING!
                        </div>
                    )}
                </div>

            </div>
        </div>
    )
}
