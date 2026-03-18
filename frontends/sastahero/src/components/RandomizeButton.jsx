import React, { useState } from 'react';
import useHeroStore from '../store/useHeroStore.js';

const RandomizeButton = () => {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const setRandomHero = useHeroStore((s) => s.setRandomHero);

  const handleRandomize = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/sastahero/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({}),
      });
      if (!res.ok) throw new Error('Failed to generate hero');
      const data = await res.json();
      setRandomHero(data.hero_class, data.stats);
    } catch (err) {
      setError('Could not connect to server');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <button
        onClick={handleRandomize}
        disabled={loading}
        className="border-brutal bg-sasta-white text-sasta-black px-6 py-3 font-zero font-bold shadow-brutal hover:bg-sasta-black hover:text-sasta-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed w-full"
      >
        {loading ? 'ROLLING...' : '🎲 RANDOMIZE HERO'}
      </button>
      {error && (
        <p className="text-xs font-zero mt-2 text-red-600">{error}</p>
      )}
    </div>
  );
};

export default RandomizeButton;
