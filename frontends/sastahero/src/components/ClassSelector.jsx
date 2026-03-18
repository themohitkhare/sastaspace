import React from 'react';
import useHeroStore, { CLASSES } from '../store/useHeroStore.js';

const CLASS_NAMES = {
  WARRIOR: 'Warrior',
  MAGE: 'Mage',
  ROGUE: 'Rogue',
  RANGER: 'Ranger',
  NECRO: 'Necromancer',
  PALADIN: 'Paladin',
};

const ClassSelector = () => {
  const heroClass = useHeroStore((s) => s.heroClass);
  const setClass = useHeroStore((s) => s.setClass);

  return (
    <div>
      <h2 className="text-xl font-bold font-zero mb-4">CHOOSE CLASS</h2>
      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        {Object.entries(CLASSES).map(([id, cls]) => (
          <button
            key={id}
            onClick={() => setClass(id)}
            className={`border-brutal p-4 text-left transition-all ${
              heroClass === id
                ? 'bg-sasta-black text-sasta-white shadow-brutal'
                : 'bg-sasta-white text-sasta-black hover:shadow-brutal'
            }`}
          >
            <div className="text-2xl mb-1">{cls.icon}</div>
            <div className="font-bold font-zero text-sm">{CLASS_NAMES[id]}</div>
            <div className="text-xs font-zero opacity-70 mt-1">{cls.desc}</div>
          </button>
        ))}
      </div>
    </div>
  );
};

export default ClassSelector;
