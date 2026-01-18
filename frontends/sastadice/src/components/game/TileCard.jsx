import { TILE_TYPE_COLORS } from './TileComponent'

const TILE_TYPE_ICONS = {
    PROPERTY: '🏠',
    TAX: '💸',
    CHANCE: '🎰',
    TRAP: '⚡',
    BUFF: '✨',
    NEUTRAL: '⬜',
    GO: '🚀',
}

export default function TileCard({ tile, owner, isVisible = true }) {
    if (!tile || !isVisible) return null

    const accentColor = TILE_TYPE_COLORS[tile.type] || TILE_TYPE_COLORS.NEUTRAL
    const icon = TILE_TYPE_ICONS[tile.type] || '⬜'
    const isOwned = !!owner
    const isPurchasable = tile.type === 'PROPERTY' && !isOwned && tile.price > 0
    const ownerBgColor = owner ? `${owner.color}4D` : '#FFFFFF'

    return (
        <div
            className="tile-card border-brutal-sm shadow-brutal-sm p-3 w-full max-w-[180px] animate-scale-in"
            style={{
                borderColor: owner?.color || accentColor,
                borderWidth: owner ? '4px' : '3px',
                backgroundColor: ownerBgColor,
            }}
        >
            <div
                className="text-center py-1 px-2 -mx-3 -mt-3 mb-2 font-zero font-bold text-xs"
                style={{ backgroundColor: accentColor, color: '#000' }}
            >
                {icon} {tile.type === 'CHANCE' ? 'SASTA EVENT' : tile.type}
            </div>

            <div className="font-data font-bold text-sm text-center mb-2 leading-tight">
                {tile.name.toUpperCase()}
            </div>

            {isOwned && (
                <div
                    className="flex items-center justify-center gap-2 py-1 px-2 mb-2 border-2 border-black"
                    style={{ backgroundColor: owner.color }}
                >
                    <div className="w-5 h-5 rounded-full bg-white border-2 border-black flex items-center justify-center font-data text-xs font-bold">
                        {owner.name?.charAt(0)?.toUpperCase()}
                    </div>
                    <span className="font-data font-bold text-xs text-white drop-shadow-sm">
                        {owner.name?.toUpperCase()}
                    </span>
                </div>
            )}

            <div className="space-y-1 text-center font-data text-xs">
                {isPurchasable && (
                    <div className="flex justify-between px-2 py-1 bg-sasta-accent border-brutal-sm">
                        <span>PRICE:</span>
                        <span className="font-bold">${tile.price}</span>
                    </div>
                )}

                {isOwned && tile.rent > 0 && (
                    <div className="flex justify-between px-2 py-2 bg-red-500 text-white border-brutal-sm">
                        <span className="font-bold">RENT:</span>
                        <span className="font-bold text-lg">${tile.rent}</span>
                    </div>
                )}

                {tile.type === 'TAX' && tile.tax_amount && (
                    <div className="flex justify-between px-2 py-1 bg-red-100 border-brutal-sm">
                        <span>TAX:</span>
                        <span className="font-bold text-red-600">${tile.tax_amount}</span>
                    </div>
                )}

                {tile.type === 'GO' && (
                    <div className="py-1 px-2 bg-sasta-accent border-brutal-sm font-bold">
                        COLLECT GO BONUS!
                    </div>
                )}

                {tile.type === 'CHANCE' && (
                    <div className="py-1 px-2 bg-yellow-100 border-brutal-sm">
                        RANDOM EVENT
                    </div>
                )}
            </div>
        </div>
    )
}

