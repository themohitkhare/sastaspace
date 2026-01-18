import { useState } from 'react'

export default function IncomingTradeAlert({ offer, initiator, myPlayer, tiles, onAccept, onDecline }) {
    const [isProcessing, setIsProcessing] = useState(false)

    const offeredTiles = tiles.filter(t => offer.offering_properties.includes(t.id))
    const requestedTiles = tiles.filter(t => offer.requesting_properties.includes(t.id))

    const handleAction = async (actionFn) => {
        setIsProcessing(true)
        try {
            await actionFn(offer.id)
        } finally {
            setIsProcessing(false)
        }
    }

    return (
        <div className="fixed top-20 right-4 z-50 w-80 bg-sasta-white border-brutal shadow-brutal-lg animate-slide-in">
            <div className="bg-blue-600 text-white p-2 font-bold font-zero flex justify-between items-center">
                <span>Incoming Trade!</span>
                <span className="text-xs opacity-75">{initiator?.name}</span>
            </div>

            <div className="p-3 text-xs">
                <div className="flex gap-2">
                    <div className="flex-1 bg-green-50 p-2 border border-green-200">
                        <div className="font-bold text-green-700 mb-1">THEY GIVE:</div>
                        {offer.offering_cash > 0 && <div className="font-mono font-bold">+${offer.offering_cash}</div>}
                        {offeredTiles.map(t => <div key={t.id} className="truncate">• {t.name}</div>)}
                        {offer.offering_cash === 0 && offeredTiles.length === 0 && <div className="italic opacity-50">Nothing</div>}
                    </div>

                    <div className="flex-1 bg-red-50 p-2 border border-red-200">
                        <div className="font-bold text-red-700 mb-1">YOU GIVE:</div>
                        {offer.requesting_cash > 0 && <div className="font-mono font-bold">-${offer.requesting_cash}</div>}
                        {requestedTiles.map(t => <div key={t.id} className="truncate">• {t.name}</div>)}
                        {offer.requesting_cash === 0 && requestedTiles.length === 0 && <div className="italic opacity-50">Nothing</div>}
                    </div>
                </div>
            </div>

            <div className="p-2 bg-gray-50 flex gap-2">
                <button
                    onClick={() => handleAction(onDecline)}
                    disabled={isProcessing}
                    className="flex-1 border-brutal-sm bg-white hover:bg-red-100 py-1 font-bold font-data text-xs"
                >
                    DECLINE
                </button>
                <button
                    onClick={() => handleAction(onAccept)}
                    disabled={isProcessing}
                    className="flex-1 border-brutal-sm bg-sasta-accent hover:bg-green-400 py-1 font-bold font-data text-xs shadow-brutal-sm"
                >
                    ACCEPT
                </button>
            </div>
        </div>
    )
}
