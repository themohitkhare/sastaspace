import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

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
      .then(r => r.json()).then(setData).catch(() => setError(true));
  }, [playerId]);

  if (error) {
    return (<div data-testid="collection-error" role="alert" className="flex-1 flex items-center justify-center bg-black text-white"><div className="text-center"><p className="text-lg font-bold font-zero text-red-400">FAILED TO LOAD</p><button className="mt-3 px-4 py-2 border-brutal-sm font-zero font-bold text-sm bg-black text-white hover:bg-sasta-accent hover:text-black transition-colors" onClick={() => { setError(false); setData(null); }}>RETRY</button></div></div>);
  }
  if (!data) {
    return <div data-testid="collection-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white"><p className="font-zero font-bold">LOADING...</p></div>;
  }

  const filtered = filter ? data.entries.filter(e => e.rarity === filter) : data.entries;

  return (
    <div data-testid="collection-book" className="flex-1 bg-black text-white p-3 overflow-y-auto">
      <h2 className="text-xl font-bold font-zero uppercase tracking-widest mb-1">COLLECTION</h2>
      <p className="text-xs font-zero mb-3 opacity-60">{data.discovered}/{data.total} DISCOVERED</p>
      <div className="flex gap-1.5 mb-3 flex-wrap" role="tablist" aria-label="Filter by rarity">
        <button role="tab" aria-selected={!filter} className={`text-[10px] px-2 py-1 font-zero font-bold border-brutal-sm uppercase tracking-wider ${!filter ? 'bg-sasta-accent text-black' : 'bg-black text-white hover:bg-white hover:text-black'} transition-colors`} onClick={() => setFilter(null)}>ALL</button>
        {['COMMON', 'UNCOMMON', 'RARE', 'EPIC', 'LEGENDARY'].map(r => (
          <button key={r} role="tab" aria-selected={filter === r} className={`text-[10px] px-2 py-1 font-zero font-bold border-brutal-sm uppercase tracking-wider ${filter === r ? 'bg-sasta-accent text-black' : 'bg-black text-white hover:bg-white hover:text-black'} transition-colors`} onClick={() => setFilter(r)}>{r}</button>
        ))}
      </div>
      <div className="grid grid-cols-4 gap-1.5" role="list" aria-label="Card collection">
        {filtered.map((entry) => (
          <div key={entry.identity_id} role="listitem" data-testid={`collection-entry-${entry.identity_id}`} aria-label={entry.discovered ? `${entry.name}, ${entry.rarity}` : 'Undiscovered card'} className={`border-brutal-sm p-2 text-center ${entry.discovered ? 'discovery-reveal' : 'opacity-30'}`}>
            <div className="text-sm mb-0.5" aria-hidden="true">{entry.discovered ? entry.types.map(t => TYPE_ICONS[t] || '?').join('') : '?'}</div>
            <div className="text-[10px] font-bold font-zero truncate">{entry.discovered ? entry.name : '???'}</div>
            <div className="text-[8px] opacity-50 font-zero mt-0.5 uppercase">{entry.rarity}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
