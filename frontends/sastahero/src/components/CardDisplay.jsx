import React from 'react';

const TYPE_TEXT_COLORS = {
  CREATION: 'text-amber-200',
  PROTECTION: 'text-blue-200',
  DESTRUCTION: 'text-red-200',
  ENERGY: 'text-amber-900',
  POWER: 'text-purple-200',
};

const TYPE_ICONS = {
  CREATION: '\u2726',
  PROTECTION: '\u25C6',
  DESTRUCTION: '\u2715',
  ENERGY: '\u2600',
  POWER: '\u2B1F',
};

export default function CardDisplay({ card, totalCards, currentIndex, className = '' }) {
  if (!card) return null;

  const primaryType = card.types[0];
  const textColor = TYPE_TEXT_COLORS[primaryType] || 'text-white';

  return (
    <div
      data-testid="card-display"
      role="article"
      aria-label={`${card.name} card, ${card.rarity} rarity, ${card.content_type} type`}
      className={`w-full h-full flex flex-col items-center justify-center p-6 scanline-overlay border-brutal card-gradient-${primaryType} rarity-${card.rarity} ${className}`}
    >
      {/* Card counter */}
      <div className="absolute top-4 right-4 text-sm font-bold opacity-60" aria-label={`Card ${currentIndex + 1} of ${totalCards}`}>
        {currentIndex + 1}/{totalCards}
      </div>

      {/* Type badges */}
      <div className="flex gap-2 mb-4" role="list" aria-label="Card types">
        {card.types.map((type) => (
          <span
            key={type}
            role="listitem"
            className="text-2xl"
            aria-label={type}
            data-testid={`type-badge-${type}`}
          >
            {TYPE_ICONS[type] || '?'}
          </span>
        ))}
      </div>

      {/* Rarity */}
      <div className="text-xs uppercase tracking-widest font-bold mb-2 opacity-70" data-testid="rarity-label">
        {card.rarity}
      </div>

      {/* Card name */}
      <h2 className="text-3xl font-bold mb-6 text-center tracking-tight" data-testid="card-name">
        {card.name}
      </h2>

      {/* Content */}
      {card.content_type !== 'RESOURCE' && card.text && (
        <p className={`text-lg text-center leading-relaxed max-w-sm ${textColor}`} data-testid="card-text"
          style={primaryType === 'ENERGY' ? { textShadow: '0 1px 2px rgba(255,255,255,0.6)' } : undefined}>
          {card.text}
        </p>
      )}

      {card.content_type === 'RESOURCE' && (
        <p className="text-lg text-center opacity-60" data-testid="card-text">
          +{card.shard_yield} shards
        </p>
      )}

      {/* Content type badge */}
      <div className="mt-6 text-xs uppercase tracking-wider opacity-50">
        {card.content_type}
      </div>

      {/* Community count */}
      {card.community_count > 0 && (
        <div className="mt-2 text-xs opacity-40" aria-label={`${card.community_count} players have this card`}>
          {card.community_count} players have this
        </div>
      )}

      {/* Shard yield */}
      <div className="mt-4 text-sm font-bold opacity-60" data-testid="shard-yield">
        Yield: {card.shard_yield} {card.shard_yield === 1 ? 'shard' : 'shards'}
      </div>
    </div>
  );
}
