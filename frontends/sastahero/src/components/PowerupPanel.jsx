import React, { useState } from 'react';
import useGameStore from '../store/useGameStore';

const POWERUPS = [
  { type: 'REROLL', name: 'Reroll', icon: '\u21BB', desc: 'Swap current card', cost: '3 of any type' },
  { type: 'PEEK', name: 'Peek', icon: '\u25CE', desc: 'Preview next 3 cards', cost: '2 of any type' },
  { type: 'MAGNETIZE', name: 'Magnetize', icon: '\u2295', desc: '3+ cards of chosen type', cost: '5 of one type' },
  { type: 'FUSION_BOOST', name: 'Fusion', icon: '\u26A1', desc: '2x combo drop rate', cost: '1 of each type' },
  { type: 'QUIZ_SHIELD', name: 'Shield', icon: '\u25C8', desc: 'Second quiz chance', cost: '4 of any type' },
  { type: 'LUCKY_DRAW', name: 'Lucky', icon: '\u2605', desc: 'Force rare+ card', cost: '3 of 3 types' },
];

export default function PowerupPanel({ isOpen, onClose }) {
  const { shards, purchasePowerup } = useGameStore();
  const [buying, setBuying] = useState(null);

  if (!isOpen) return null;

  const handlePurchase = async (type) => {
    setBuying(type);
    await purchasePowerup(type);
    setBuying(null);
  };

  const canAfford = (type) => {
    const vals = Object.values(shards);
    switch (type) {
      case 'REROLL': return vals.some(v => v >= 3);
      case 'PEEK': return vals.some(v => v >= 2);
      case 'MAGNETIZE': return vals.some(v => v >= 5);
      case 'FUSION_BOOST': return vals.every(v => v >= 1);
      case 'QUIZ_SHIELD': return vals.some(v => v >= 4);
      case 'LUCKY_DRAW': return vals.filter(v => v >= 3).length >= 3;
      default: return false;
    }
  };

  return (
    <div data-testid="powerup-panel" className="fixed inset-0 z-50 flex items-end" role="dialog" aria-label="Powerups panel">
      <div className="absolute inset-0 bg-black bg-opacity-50" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full bg-black text-white border-t-4 border-white p-6 max-h-[70vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold">POWERUPS</h3>
          <button onClick={onClose} className="text-2xl font-bold" aria-label="Close powerups panel">{'\u2715'}</button>
        </div>
        <div className="grid grid-cols-2 gap-3" role="list" aria-label="Available powerups">
          {POWERUPS.map((p) => {
            const affordable = canAfford(p.type);
            return (
              <button
                key={p.type}
                role="listitem"
                data-testid={`powerup-${p.type}`}
                aria-label={`${p.name}: ${p.desc}. Cost: ${p.cost}. ${affordable ? 'Available' : 'Not enough shards'}`}
                className={`p-3 border-2 text-left ${affordable ? 'border-white hover:bg-white hover:text-black' : 'border-gray-600 opacity-40 cursor-not-allowed'}`}
                disabled={!affordable || buying === p.type}
                onClick={() => handlePurchase(p.type)}
              >
                <div className="text-2xl mb-1">{p.icon}</div>
                <div className="text-sm font-bold">{p.name}</div>
                <div className="text-xs opacity-60">{p.desc}</div>
                <div className="text-xs mt-1 opacity-40">{p.cost}</div>
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
}
