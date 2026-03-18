import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

export default function KnowledgeBank() {
  const { playerId } = useGameStore();
  const [data, setData] = useState(null);
  const [activeCategory, setActiveCategory] = useState(null);

  useEffect(() => {
    const url = activeCategory
      ? `/api/v1/sastahero/knowledge?player_id=${playerId}&category=${activeCategory}`
      : `/api/v1/sastahero/knowledge?player_id=${playerId}`;
    fetch(url)
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, [playerId, activeCategory]);

  if (!data) {
    return <div data-testid="knowledge-loading" className="flex-1 flex items-center justify-center bg-black text-white"><p>Loading...</p></div>;
  }

  return (
    <div data-testid="knowledge-bank" className="flex-1 bg-black text-white p-4 overflow-y-auto">
      <h2 className="text-2xl font-bold mb-2">KNOWLEDGE BANK</h2>
      <p className="text-sm mb-4 opacity-60">{data.total} facts saved</p>

      {/* Category filters */}
      {data.categories.length > 0 && (
        <div className="flex gap-2 mb-4 flex-wrap">
          <button
            className={`text-xs px-2 py-1 border ${!activeCategory ? 'bg-white text-black' : 'border-white'}`}
            onClick={() => setActiveCategory(null)}
          >ALL</button>
          {data.categories.map(cat => (
            <button
              key={cat}
              className={`text-xs px-2 py-1 border ${activeCategory === cat ? 'bg-white text-black' : 'border-white'}`}
              onClick={() => setActiveCategory(cat)}
            >{cat}</button>
          ))}
        </div>
      )}

      {data.facts.length === 0 && (
        <div className="text-center opacity-40 mt-20">
          <p className="text-lg">No facts saved yet.</p>
          <p className="text-sm mt-2">Swipe knowledge cards RIGHT to save them here.</p>
        </div>
      )}

      {data.facts.map((fact, i) => (
        <div key={i} className="mb-3 p-3 border-2 border-gray-600">
          <p className="text-sm leading-relaxed">{fact.text}</p>
          <p className="text-[10px] opacity-40 mt-1 uppercase">{fact.category}</p>
        </div>
      ))}
    </div>
  );
}
