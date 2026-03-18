import React from 'react';
import useHeroStore, { CLASSES, STAT_NAMES, TOTAL_BONUS_POINTS, STAT_MAX } from '../store/useHeroStore.js';

const StatAllocator = () => {
  const heroClass = useHeroStore((s) => s.heroClass);
  const bonusStats = useHeroStore((s) => s.bonusStats);
  const incrementStat = useHeroStore((s) => s.incrementStat);
  const decrementStat = useHeroStore((s) => s.decrementStat);
  const getStats = useHeroStore((s) => s.getStats);
  const getPointsRemaining = useHeroStore((s) => s.getPointsRemaining);

  const stats = getStats();
  const pointsRemaining = getPointsRemaining();
  const baseStats = CLASSES[heroClass].baseStats;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-bold font-zero">ALLOCATE STATS</h2>
        <span className="font-zero text-sm border-brutal-sm px-3 py-1 bg-sasta-black text-sasta-white">
          {pointsRemaining} / {TOTAL_BONUS_POINTS} pts left
        </span>
      </div>
      <div className="space-y-3">
        {STAT_NAMES.map((stat) => {
          const current = stats[stat];
          const base = baseStats[stat];
          const bonus = bonusStats[stat];
          const pct = Math.round((current / STAT_MAX) * 100);
          const canInc = pointsRemaining > 0 && current < STAT_MAX;
          const canDec = bonus > 0;

          return (
            <div key={stat} className="flex items-center gap-3">
              <span className="font-zero font-bold text-sm w-10">{stat}</span>
              <div className="flex-1 border-brutal-sm h-5 bg-sasta-white overflow-hidden">
                <div
                  className="h-full bg-sasta-black transition-all duration-150"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="font-zero font-bold text-sm w-8 text-right">{current}</span>
              <div className="flex gap-1">
                <button
                  onClick={() => decrementStat(stat)}
                  disabled={!canDec}
                  className="border-brutal-sm w-7 h-7 font-zero font-bold bg-sasta-white hover:bg-sasta-black hover:text-sasta-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  aria-label={`Decrease ${stat}`}
                >
                  −
                </button>
                <button
                  onClick={() => incrementStat(stat)}
                  disabled={!canInc}
                  className="border-brutal-sm w-7 h-7 font-zero font-bold bg-sasta-white hover:bg-sasta-black hover:text-sasta-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                  aria-label={`Increase ${stat}`}
                >
                  +
                </button>
              </div>
              {bonus > 0 && (
                <span className="font-zero text-xs text-sasta-accent font-bold w-8">+{bonus}</span>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
};

export default StatAllocator;
