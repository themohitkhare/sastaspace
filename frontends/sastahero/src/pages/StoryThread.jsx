import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

export default function StoryThread() {
  const { playerId } = useGameStore();
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    fetch(`/api/v1/sastahero/story?player_id=${playerId}`)
      .then(r => r.json()).then(setData).catch(() => setError(true));
  }, [playerId]);

  if (error) {
    return (<div data-testid="story-error" role="alert" className="flex-1 flex items-center justify-center bg-black text-white"><div className="text-center"><p className="text-lg font-bold font-zero text-red-400">FAILED TO LOAD</p><button className="mt-3 px-4 py-2 border-brutal-sm font-zero font-bold text-sm bg-black text-white hover:bg-sasta-accent hover:text-black transition-colors" onClick={() => { setError(false); setData(null); }}>RETRY</button></div></div>);
  }
  if (!data) {
    return <div data-testid="story-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white"><p className="font-zero font-bold">LOADING...</p></div>;
  }

  return (
    <div data-testid="story-thread" className="flex-1 bg-black text-white p-3 overflow-y-auto">
      <h2 className="text-xl font-bold font-zero uppercase tracking-widest mb-1">YOUR STORY</h2>
      <p className="text-xs font-zero mb-4 opacity-60">{data.total_chapters} CHAPTERS WRITTEN</p>
      {data.chapters.length === 0 && data.current_fragments.length === 0 && (
        <div className="text-center opacity-40 mt-20 font-zero">
          <p className="text-lg">&gt; NO STORY YET.</p>
          <p className="text-sm mt-2">&gt; SWIPE CARDS UP TO BUILD YOUR STORY.</p>
        </div>
      )}
      {data.current_fragments.length > 0 && (
        <div className="mb-4 p-3 border-brutal-sm border-dashed border-gray-600">
          <h3 className="text-[10px] uppercase tracking-widest font-zero font-bold opacity-50 mb-2">IN PROGRESS...</h3>
          <p className="text-xs font-zero leading-relaxed opacity-80">
            {data.current_fragments.map((f, i) => (<span key={i} className="block">&gt; {f}</span>))}
          </p>
        </div>
      )}
      {[...data.chapters].reverse().map((ch) => (
        <article key={ch.number} className="mb-3 p-3 border-brutal-sm" aria-label={`Chapter ${ch.number}`}>
          <h3 className="text-[10px] font-bold font-zero uppercase tracking-widest opacity-60 mb-1">CHAPTER {ch.number}</h3>
          <p className="text-xs font-zero leading-relaxed">&gt; {ch.text}</p>
        </article>
      ))}
    </div>
  );
}
