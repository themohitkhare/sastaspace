import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

export default function StoryThread() {
  const { playerId } = useGameStore();
  const [data, setData] = useState(null);

  useEffect(() => {
    fetch(`/api/v1/sastahero/story?player_id=${playerId}`)
      .then(r => r.json())
      .then(setData)
      .catch(() => {});
  }, [playerId]);

  if (!data) {
    return <div data-testid="story-loading" className="flex-1 flex items-center justify-center bg-black text-white"><p>Loading...</p></div>;
  }

  return (
    <div data-testid="story-thread" className="flex-1 bg-black text-white p-4 overflow-y-auto">
      <h2 className="text-2xl font-bold mb-2">YOUR STORY</h2>
      <p className="text-sm mb-6 opacity-60">{data.total_chapters} chapters written</p>

      {data.chapters.length === 0 && data.current_fragments.length === 0 && (
        <div className="text-center opacity-40 mt-20">
          <p className="text-lg">No story yet.</p>
          <p className="text-sm mt-2">Swipe cards UP to build your story.</p>
        </div>
      )}

      {/* Current fragments */}
      {data.current_fragments.length > 0 && (
        <div className="mb-6 p-4 border-2 border-dashed border-gray-600">
          <h3 className="text-xs uppercase tracking-wider opacity-50 mb-2">In progress...</h3>
          <p className="text-sm leading-relaxed opacity-80">{data.current_fragments.join(' ')}</p>
        </div>
      )}

      {/* Chapters */}
      {[...data.chapters].reverse().map((ch) => (
        <div key={ch.number} className="mb-6 p-4 border-2 border-white">
          <h3 className="text-sm font-bold mb-2 opacity-60">Chapter {ch.number}</h3>
          <p className="text-sm leading-relaxed">{ch.text}</p>
        </div>
      ))}
    </div>
  );
}
