import { TILE_TYPE_COLORS } from './TileComponent'

export default function PropertyManagerModal({ tiles, playerId, onSelectTile, onClose }) {
    if (!tiles || !playerId) return null

    const ownedProperties = tiles.filter(t => t.type === 'PROPERTY' && t.owner_id === playerId)

    if (ownedProperties.length === 0) {
        return (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
                <div className="bg-sasta-white border-brutal-lg shadow-brutal-lg max-w-sm w-full p-4 text-center" onClick={e => e.stopPropagation()}>
                    <div className="font-zero text-lg mb-4">NO PROPERTIES OWNED</div>
                    <button onClick={onClose} className="bg-sasta-black text-sasta-accent px-4 py-2 font-zero">CLOSE</button>
                </div>
            </div>
        )
    }

    const groupedByColor = ownedProperties.reduce((acc, tile) => {
        const color = tile.color || 'OTHER'
        if (!acc[color]) acc[color] = []
        acc[color].push(tile)
        return acc
    }, {})

    const colorSetStatus = {}
    for (const color of Object.keys(groupedByColor)) {
        const allOfColor = tiles.filter(t => t.type === 'PROPERTY' && t.color === color)
        const ownedOfColor = allOfColor.filter(t => t.owner_id === playerId)
        colorSetStatus[color] = {
            owned: ownedOfColor.length,
            total: allOfColor.length,
            isComplete: ownedOfColor.length === allOfColor.length
        }
    }

    const getLevelBadge = (level) => {
        if (level === 0) return null
        if (level === 1) return <span className="text-yellow-500">⚡</span>
        if (level === 2) return <span className="text-yellow-500">⚡⚡</span>
        return null
    }

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4" onClick={onClose}>
            <div className="bg-sasta-white border-brutal-lg shadow-brutal-lg max-w-md w-full max-h-[80vh] overflow-hidden flex flex-col" onClick={e => e.stopPropagation()}>
                <div className="p-3 bg-sasta-black text-sasta-accent font-zero text-lg text-center border-b-2 border-sasta-black flex justify-between items-center">
                    <span>🏠 YOUR PROPERTIES</span>
                    <button onClick={onClose} className="text-xs bg-sasta-accent text-sasta-black px-2 py-1">X</button>
                </div>

                <div className="flex-1 overflow-y-auto p-3 space-y-3">
                    {Object.entries(groupedByColor).map(([color, colorTiles]) => (
                        <div key={color} className="border-brutal-sm p-2">
                            <div className="flex items-center gap-2 mb-2 pb-1 border-b border-gray-300">
                                <div
                                    className="w-4 h-4 border border-black"
                                    style={{ backgroundColor: TILE_TYPE_COLORS.PROPERTY || '#888' }}
                                ></div>
                                <span className="font-data font-bold text-sm">{color}</span>
                                <span className={`text-xs ml-auto ${colorSetStatus[color].isComplete ? 'text-green-600 font-bold' : 'text-zinc-400'}`}>
                                    {colorSetStatus[color].isComplete ? '✓ FULL SET' : `${colorSetStatus[color].owned}/${colorSetStatus[color].total}`}
                                </span>
                            </div>

                            <div className="space-y-1">
                                {colorTiles.map(tile => (
                                    <button
                                        key={tile.id}
                                        onClick={() => {
                                            onSelectTile(tile)
                                            onClose()
                                        }}
                                        className="w-full flex justify-between items-center p-2 bg-white hover:bg-sasta-accent/20 border border-gray-200 transition-colors text-left"
                                    >
                                        <div>
                                            <div className="font-data font-bold text-sm">{tile.name}</div>
                                            <div className="text-xs text-zinc-500">
                                                Rent: ${tile.rent} {getLevelBadge(tile.upgrade_level)}
                                            </div>
                                        </div>
                                        <div className="text-right">
                                            {colorSetStatus[color].isComplete && tile.upgrade_level < 2 && (
                                                <span className="text-xs bg-sasta-accent text-sasta-black px-1 font-bold">CAN UPGRADE</span>
                                            )}
                                            {tile.upgrade_level === 2 && (
                                                <span className="text-xs bg-green-500 text-white px-1 font-bold">MAX</span>
                                            )}
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>
                    ))}
                </div>

                <div className="p-2 bg-zinc-100 text-center text-xs text-zinc-500 font-data border-t border-gray-300">
                    Click a property to view details and upgrade
                </div>
            </div>
        </div>
    )
}
