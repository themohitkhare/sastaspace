import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

const RARITY_COLORS = {
  COMMON: 'border-gray-400',
  UNCOMMON: 'border-green-400',
  RARE: 'border-blue-400',
  EPIC: 'border-purple-400',
  LEGENDARY: 'border-yellow-400',
};

const TYPE_ICONS = {
  CREATION: '\u2726', PROTECTION: '\u25C6', DESTRUCTION: '\u2715', ENERGY: '\u2600', POWER: '\u2B1F',
};

export default function CollectionBook() {
  const { playerId } = useGameStore();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [filter, setFilter] = useState(null);

  useEffect(() => {
    fetch(`/api/v1/sastahero/collection?player_id=${playerId}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => setError(true));
  }, [playerId]);

  if (error) {
    return (
      <div data-testid="collection-error" role="alert" className="flex-1 flex items-center justify-center bg-black text-white">
        <div className="text-center">
          <p className="text-lg font-bold text-red-400">Failed to load collection</p>
          <button className="mt-3 px-4 py-2 border-2 border-white text-sm" onClick={() => { setError(false); setData(null); }}>Retry</button>
        </div>
      </div>
    );
  }

  if (!data) {
    return <div data-testid="collection-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white"><p>Loading...</p></div>;
  }

  const filtered = filter ? data.entries.filter(e => e.rarity === filter) : data.entries;

  return (
    <div data-testid="collection-book" className="flex-1 bg-black text-white p-4 overflow-y-auto">
      <h2 className="text-2xl font-bold mb-2">COLLECTION</h2>
      <p className="text-sm mb-4 opacity-60">{data.discovered}/{data.total} discovered</p>

      {/* Rarity filters */}
      <div className="flex gap-2 mb-4 flex-wrap" role="tablist" aria-label="Filter by rarity">
        <button
          role="tab"
          aria-selected={!filter}
          className={`text-xs px-2 py-1 border ${!filter ? 'bg-white text-black' : 'border-white'}`}
          onClick={() => setFilter(null)}
        >ALL</button>
        {['COMMON', 'UNCOMMON', 'RARE', 'EPIC', 'LEGENDARY'].map(r => (
          <button
            key={r}
            role="tab"
            aria-selected={filter === r}
            className={`text-xs px-2 py-1 border ${filter === r ? 'bg-white text-black' : 'border-white'}`}
            onClick={() => setFilter(r)}
          >{r}</button>
        ))}
      </div>

      {/* Grid */}
      <div className="grid grid-cols-3 gap-2" role="list" aria-label="Card collection">
        {filtered.map((entry) => (
          <div
            key={entry.identity_id}
            role="listitem"
            data-testid={`collection-entry-${entry.identity_id}`}
            aria-label={entry.discovered ? `${entry.name}, ${entry.rarity}` : 'Undiscovered card'}
            className={`border-2 p-3 text-center ${RARITY_COLORS[entry.rarity] || 'border-gray-600'} ${entry.discovered ? '' : 'opacity-30'}`}
          >
            <div className="text-lg mb-1" aria-hidden="true">
              {entry.discovered ? entry.types.map(t => TYPE_ICONS[t] || '?').join('') : '?'}
            </div>
            <div className="text-xs font-bold truncate">
              {entry.discovered ? entry.name : '???'}
            </div>
            <div className="text-[10px] opacity-50 mt-1">{entry.rarity}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
