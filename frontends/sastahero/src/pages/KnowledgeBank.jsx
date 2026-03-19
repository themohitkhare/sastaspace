import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

export default function KnowledgeBank() {
  const { playerId } = useGameStore();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);
  const [activeCategory, setActiveCategory] = useState(null);

  useEffect(() => {
    const url = activeCategory
      ? `/api/v1/sastahero/knowledge?player_id=${playerId}&category=${activeCategory}`
      : `/api/v1/sastahero/knowledge?player_id=${playerId}`;
    fetch(url).then(r => r.json()).then(setData).catch(() => setError(true));
  }, [playerId, activeCategory]);

  if (error) {
    return (<div data-testid="knowledge-error" role="alert" className="flex-1 flex items-center justify-center bg-black text-white"><div className="text-center"><p className="text-lg font-bold font-zero text-red-400">FAILED TO LOAD</p><button className="mt-3 px-4 py-2 border-brutal-sm font-zero font-bold text-sm bg-black text-white hover:bg-sasta-accent hover:text-black transition-colors" onClick={() => { setError(false); setData(null); }}>RETRY</button></div></div>);
  }
  if (!data) {
    return <div data-testid="knowledge-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white"><p className="font-zero font-bold">LOADING...</p></div>;
  }

  return (
    <div data-testid="knowledge-bank" className="flex-1 bg-black text-white p-3 overflow-y-auto">
      <h2 className="text-xl font-bold font-zero uppercase tracking-widest mb-1">KNOWLEDGE BANK</h2>
      <p className="text-xs font-zero mb-3 opacity-60">{data.total} FACTS SAVED</p>
      {data.categories.length > 0 && (
        <div className="flex gap-1.5 mb-3 flex-wrap" role="tablist" aria-label="Filter by category">
          <button role="tab" aria-selected={!activeCategory} className={`text-[10px] px-2 py-1 font-zero font-bold border-brutal-sm uppercase tracking-wider ${!activeCategory ? 'bg-sasta-accent text-black' : 'bg-black text-white hover:bg-white hover:text-black'} transition-colors`} onClick={() => setActiveCategory(null)}>ALL</button>
          {data.categories.map(cat => (
            <button key={cat} role="tab" aria-selected={activeCategory === cat} className={`text-[10px] px-2 py-1 font-zero font-bold border-brutal-sm uppercase tracking-wider ${activeCategory === cat ? 'bg-sasta-accent text-black' : 'bg-black text-white hover:bg-white hover:text-black'} transition-colors`} onClick={() => setActiveCategory(cat)}>{cat}</button>
          ))}
        </div>
      )}
      {data.facts.length === 0 && (
        <div className="text-center opacity-40 mt-20 font-zero">
          <p className="text-lg">&gt; NO FACTS SAVED YET.</p>
          <p className="text-sm mt-2">&gt; SWIPE KNOWLEDGE CARDS RIGHT TO SAVE THEM.</p>
        </div>
      )}
      <div role="list" aria-label="Saved facts">
        {data.facts.map((fact, i) => (
          <div key={i} role="listitem" className="mb-2 p-3 border-brutal-sm">
            <p className="text-xs font-zero leading-relaxed">{fact.text}</p>
            <p className="text-[10px] opacity-40 mt-1 font-zero font-bold uppercase tracking-wider">{fact.category}</p>
          </div>
        ))}
      </div>
    </div>
  );
}
