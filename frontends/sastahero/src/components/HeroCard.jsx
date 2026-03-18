import React from 'react';
import useHeroStore, { CLASSES, STAT_NAMES, STAT_MAX } from '../store/useHeroStore.js';

const CLASS_NAMES = {
  WARRIOR: 'Warrior',
  MAGE: 'Mage',
  ROGUE: 'Rogue',
  RANGER: 'Ranger',
  NECRO: 'Necromancer',
  PALADIN: 'Paladin',
};

const HeroCard = ({ forwardRef }) => {
  const heroClass = useHeroStore((s) => s.heroClass);
  const getStats = useHeroStore((s) => s.getStats);
  const getTotalPower = useHeroStore((s) => s.getTotalPower);

  const stats = getStats();
  const totalPower = getTotalPower();
  const cls = CLASSES[heroClass];

  return (
    <div
      ref={forwardRef}
      className="border-brutal-lg bg-sasta-white shadow-brutal-lg p-6 w-full max-w-xs"
      data-testid="hero-card"
    >
      <div className="text-center mb-4">
        <div className="text-5xl mb-2">{cls.icon}</div>
        <h3 className="text-2xl font-bold font-zero">{CLASS_NAMES[heroClass]}</h3>
        <p className="text-xs font-zero text-sasta-black/60 mt-1">{cls.desc}</p>
      </div>

      <div className="border-brutal-sm mb-4" />

      <div className="space-y-2">
        {STAT_NAMES.map((stat) => {
          const val = stats[stat];
          const pct = Math.round((val / STAT_MAX) * 100);
          return (
            <div key={stat} className="flex items-center gap-2">
              <span className="font-zero font-bold text-xs w-8">{stat}</span>
              <div className="flex-1 border-brutal-sm h-3 bg-sasta-white overflow-hidden">
                <div
                  className="h-full bg-sasta-black"
                  style={{ width: `${pct}%` }}
                />
              </div>
              <span className="font-zero font-bold text-xs w-6 text-right">{val}</span>
            </div>
          );
        })}
      </div>

      <div className="border-brutal-sm mt-4 mb-3" />

      <div className="flex items-center justify-between">
        <span className="font-zero text-xs font-bold">TOTAL POWER</span>
        <span className="font-zero text-xl font-bold border-brutal-sm px-3 py-1 bg-sasta-black text-sasta-white">
          {totalPower}
        </span>
      </div>
    </div>
  );
};

export default HeroCard;
