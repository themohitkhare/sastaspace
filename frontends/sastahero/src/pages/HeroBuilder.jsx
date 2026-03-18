import React, { useRef } from 'react';
import ClassSelector from '../components/ClassSelector.jsx';
import StatAllocator from '../components/StatAllocator.jsx';
import HeroCard from '../components/HeroCard.jsx';
import ExportButton from '../components/ExportButton.jsx';
import RandomizeButton from '../components/RandomizeButton.jsx';
import useHeroStore from '../store/useHeroStore.js';

const HeroBuilder = () => {
  const cardRef = useRef(null);
  const reset = useHeroStore((s) => s.reset);

  return (
    <div className="min-h-screen bg-sasta-white">
      <header className="border-b-4 border-sasta-black bg-sasta-white sticky top-0 z-10">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold font-zero">SASTAHERO</h1>
            <p className="text-xs font-zero text-sasta-black/60">RPG HERO CARD BUILDER</p>
          </div>
          <a
            href="/"
            className="text-xs font-zero font-bold border-brutal-sm px-3 py-2 bg-sasta-black text-sasta-white hover:bg-sasta-accent hover:text-sasta-black transition-colors"
          >
            ← BACK
          </a>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-6 py-10">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-10">
          {/* Left: Controls */}
          <div className="space-y-8">
            <ClassSelector />
            <StatAllocator />
            <div className="space-y-3">
              <RandomizeButton />
              <button
                onClick={reset}
                className="border-brutal-sm bg-sasta-white text-sasta-black px-6 py-2 font-zero font-bold hover:bg-sasta-black hover:text-sasta-white transition-colors w-full text-sm"
              >
                RESET
              </button>
            </div>
          </div>

          {/* Right: Hero Card Preview + Export */}
          <div className="flex flex-col items-center gap-6">
            <HeroCard forwardRef={cardRef} />
            <div className="w-full max-w-xs">
              <ExportButton cardRef={cardRef} />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
};

export default HeroBuilder;
