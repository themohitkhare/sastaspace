import { useState, useMemo } from 'react'
import TileComponent from './TileComponent'

export default function TradeModal({ myPlayer, targetPlayer, tiles, onClose, onPropose }) {
    const [offerCash, setOfferCash] = useState(0)
    const [reqCash, setReqCash] = useState(0)
    const [selectedOfferProps, setSelectedOfferProps] = useState(new Set())
    const [selectedReqProps, setSelectedReqProps] = useState(new Set())
    const [isSubmitting, setIsSubmitting] = useState(false)

    const myProperties = useMemo(() =>
        tiles.filter(t => t.owner_id === myPlayer.id),
        [tiles, myPlayer.id]
    )

    const targetProperties = useMemo(() =>
        tiles.filter(t => t.owner_id === targetPlayer.id),
        [tiles, targetPlayer.id]
    )

    const toggleOfferProp = (id) => {
        const next = new Set(selectedOfferProps)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        setSelectedOfferProps(next)
    }

    const toggleReqProp = (id) => {
        const next = new Set(selectedReqProps)
        if (next.has(id)) next.delete(id)
        else next.add(id)
        setSelectedReqProps(next)
    }

    const handlePropose = async () => {
        if (isSubmitting) return
        setIsSubmitting(true)
        try {
            await onPropose({
                target_id: targetPlayer.id,
                offer_cash: parseInt(offerCash) || 0,
                req_cash: parseInt(reqCash) || 0,
                offer_props: Array.from(selectedOfferProps),
                req_props: Array.from(selectedReqProps)
            })
            onClose()
        } catch (e) {
            setIsSubmitting(false)
        }
    }

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 p-4">
            <div className="bg-sasta-white border-brutal w-full max-w-4xl max-h-[90vh] flex flex-col shadow-brutal-lg">
                <div className="bg-sasta-black text-white p-3 flex justify-between items-center shrink-0">
                    <h2 className="font-zero text-xl">TRADE PROPOSAL</h2>
                    <button onClick={onClose} className="text-white hover:text-sasta-accent">✕</button>
                </div>

                <div className="flex-1 overflow-hidden flex flex-col md:flex-row divide-y md:divide-y-0 md:divide-x-2 divide-sasta-black/20">
                    <div className="flex-1 p-4 bg-red-50/50 flex flex-col min-h-0">
                        <div className="flex items-center gap-2 mb-4 border-b pb-2 border-red-200">
                            <div className="font-bold font-data text-lg text-red-600">YOU GIVE</div>
                            <div className="text-xs opacity-60">({myPlayer.name})</div>
                        </div>

                        <div className="mb-4">
                            <label className="block text-xs font-bold font-data mb-1">CASH OFFER ($)</label>
                            <input
                                type="number"
                                min="0"
                                max={myPlayer.cash}
                                value={offerCash}
                                onChange={e => setOfferCash(Math.min(myPlayer.cash, parseInt(e.target.value) || 0))}
                                className="w-full border-brutal-sm p-2 font-bold font-mono"
                            />
                            <div className="text-xs text-right mt-1 opacity-50">Max: ${myPlayer.cash}</div>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            <div className="font-bold text-xs font-data mb-2 opacity-50">PROPERTIES</div>
                            <div className="grid grid-cols-1 gap-2">
                                {myProperties.map(tile => (
                                    <div
                                        key={tile.id}
                                        onClick={() => toggleOfferProp(tile.id)}
                                        className={`border-brutal-sm p-2 flex items-center gap-2 cursor-pointer transition-all ${selectedOfferProps.has(tile.id) ? 'bg-sasta-accent -translate-y-1' : 'bg-white hover:bg-gray-50'}`}
                                    >
                                        <div className={`w-4 h-4 border border-black shrink-0 ${selectedOfferProps.has(tile.id) ? 'bg-black' : ''}`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="font-bold text-xs truncate">{tile.name}</div>
                                            <div className="text-[10px] opacity-60">${tile.price}</div>
                                        </div>
                                    </div>
                                ))}
                                {myProperties.length === 0 && <div className="text-xs opacity-40 italic">No properties owned</div>}
                            </div>
                        </div>
                    </div>

                    <div className="flex-1 p-4 bg-green-50/50 flex flex-col min-h-0">
                        <div className="flex items-center gap-2 mb-4 border-b pb-2 border-green-200">
                            <div className="font-bold font-data text-lg text-green-600">YOU GET</div>
                            <div className="text-xs opacity-60">({targetPlayer.name})</div>
                        </div>

                        <div className="mb-4">
                            <label className="block text-xs font-bold font-data mb-1">CASH REQUEST ($)</label>
                            <input
                                type="number"
                                min="0"
                                value={reqCash}
                                onChange={e => setReqCash(parseInt(e.target.value) || 0)}
                                className="w-full border-brutal-sm p-2 font-bold font-mono"
                            />
                            <div className="text-xs text-right mt-1 opacity-50">Target has: ??? (Hidden)</div>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            <div className="font-bold text-xs font-data mb-2 opacity-50">PROPERTIES</div>
                            <div className="grid grid-cols-1 gap-2">
                                {targetProperties.map(tile => (
                                    <div
                                        key={tile.id}
                                        onClick={() => toggleReqProp(tile.id)}
                                        className={`border-brutal-sm p-2 flex items-center gap-2 cursor-pointer transition-all ${selectedReqProps.has(tile.id) ? 'bg-green-300 -translate-y-1' : 'bg-white hover:bg-gray-50'}`}
                                    >
                                        <div className={`w-4 h-4 border border-black shrink-0 ${selectedReqProps.has(tile.id) ? 'bg-black' : ''}`} />
                                        <div className="flex-1 min-w-0">
                                            <div className="font-bold text-xs truncate">{tile.name}</div>
                                            <div className="text-[10px] opacity-60">${tile.price}</div>
                                        </div>
                                    </div>
                                ))}
                                {targetProperties.length === 0 && <div className="text-xs opacity-40 italic">No properties owned</div>}
                            </div>
                        </div>
                    </div>
                </div>

                <div className="p-4 bg-white border-t border-black flex justify-end gap-2 shrink-0">
                    <button onClick={onClose} className="px-6 py-3 font-bold font-zero text-sm hover:underline">CANCEL</button>
                    <button
                        onClick={handlePropose}
                        disabled={isSubmitting}
                        className="px-8 py-3 bg-sasta-black text-sasta-accent font-bold font-zero text-lg border-brutal shadow-brutal hover:translate-x-1 hover:translate-y-1 hover:shadow-none transition-all disabled:opacity-50"
                    >
                        {isSubmitting ? 'SENDING...' : 'PROPOSE TRADE'}
                    </button>
                </div>
            </div>
        </div>
    )
}
