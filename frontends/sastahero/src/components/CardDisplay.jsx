import React from 'react';

const TYPE_COLORS = {
  CREATION: { bg: 'from-amber-500 to-yellow-600', border: 'border-amber-400', text: 'text-amber-200' },
  PROTECTION: { bg: 'from-blue-500 to-slate-600', border: 'border-blue-400', text: 'text-blue-200' },
  DESTRUCTION: { bg: 'from-red-600 to-gray-800', border: 'border-red-500', text: 'text-red-200' },
  ENERGY: { bg: 'from-yellow-300 to-white', border: 'border-yellow-300', text: 'text-yellow-800' },
  POWER: { bg: 'from-purple-600 to-indigo-900', border: 'border-purple-400', text: 'text-purple-200' },
};

const RARITY_GLOW = {
  COMMON: '',
  UNCOMMON: 'shadow-[0_0_15px_rgba(100,200,100,0.3)]',
  RARE: 'shadow-[0_0_25px_rgba(50,130,250,0.5)]',
  EPIC: 'shadow-[0_0_35px_rgba(160,50,255,0.6)]',
  LEGENDARY: 'shadow-[0_0_50px_rgba(255,215,0,0.8)]',
};

const TYPE_ICONS = {
  CREATION: '✦',
  PROTECTION: '◆',
  DESTRUCTION: '✕',
  ENERGY: '☀',
  POWER: '⬟',
};

export default function CardDisplay({ card, totalCards, currentIndex }) {
  if (!card) return null;

  const primaryType = card.types[0];
  const colors = TYPE_COLORS[primaryType] || TYPE_COLORS.CREATION;
  const glow = RARITY_GLOW[card.rarity] || '';

  return (
    <div
      data-testid="card-display"
      className={`w-full h-full flex flex-col items-center justify-center p-6 bg-gradient-to-br ${colors.bg} ${glow} rounded-none border-4 ${colors.border}`}
    >
      {/* Card counter */}
      <div className="absolute top-4 right-4 text-sm font-bold opacity-60">
        {currentIndex + 1}/{totalCards}
      </div>

      {/* Type badges */}
      <div className="flex gap-2 mb-4">
        {card.types.map((type) => (
          <span
            key={type}
            className="text-2xl"
            title={type}
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
        <p className={`text-lg text-center leading-relaxed max-w-sm ${colors.text}`} data-testid="card-text">
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
        <div className="mt-2 text-xs opacity-40">
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
