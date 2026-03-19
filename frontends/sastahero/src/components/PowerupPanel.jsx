import React, { useState } from 'react';
import useGameStore from '../store/useGameStore';

const POWERUPS = [
  { type: 'REROLL', name: 'REROLL', icon: '\u21BB', desc: 'Swap current card', cost: '3 any', color: 'border-sasta-accent' },
  { type: 'PEEK', name: 'PEEK', icon: '\u25CE', desc: 'Preview next 3', cost: '2 any', color: 'border-blue-400' },
  { type: 'MAGNETIZE', name: 'MAGNET', icon: '\u2295', desc: '3+ chosen type', cost: '5 one', color: 'border-purple-400' },
  { type: 'FUSION_BOOST', name: 'FUSION', icon: '\u26A1', desc: '2x combo rate', cost: '1 each', color: 'border-yellow-400' },
  { type: 'QUIZ_SHIELD', name: 'SHIELD', icon: '\u25C8', desc: '2nd quiz chance', cost: '4 any', color: 'border-green-400' },
  { type: 'LUCKY_DRAW', name: 'LUCKY', icon: '\u2605', desc: 'Force rare+', cost: '3 of 3', color: 'border-amber-400' },
];

export default function PowerupPanel({ isOpen, onClose }) {
  const { shards, purchasePowerup } = useGameStore();
  const [buying, setBuying] = useState(null);
  const [burstType, setBurstType] = useState(null);

  if (!isOpen) return null;

  const handlePurchase = async (type) => {
    setBuying(type); setBurstType(type);
    const result = await purchasePowerup(type);
    setBuying(null);
    setTimeout(() => setBurstType(null), 600);
    if (result?.success) setTimeout(onClose, 300);
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
      <div className="absolute inset-0 bg-black bg-opacity-70" onClick={onClose} aria-hidden="true" />
      <div className="relative w-full bg-black text-white border-brutal-lg border-sasta-accent shadow-brutal-lg p-4 max-h-[70vh] overflow-y-auto panel-slide-up">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-xl font-bold font-zero uppercase tracking-widest">POWERUPS</h3>
          <button onClick={onClose} className="text-2xl font-bold font-zero text-sasta-accent hover:text-white transition-colors" aria-label="Close powerups panel">{'\u2715'}</button>
        </div>
        <div className="grid grid-cols-2 gap-3" role="list" aria-label="Available powerups">
          {POWERUPS.map((p) => {
            const affordable = canAfford(p.type);
            return (
              <div key={p.type} className="relative">
                <button role="listitem" data-testid={`powerup-${p.type}`}
                  aria-label={`${p.name}: ${p.desc}. Cost: ${p.cost}. ${affordable ? 'Available' : 'Not enough shards'}`}
                  className={`w-full p-3 text-left font-zero border-brutal-sm transition-colors ${affordable ? 'bg-black text-white hover:bg-sasta-accent hover:text-black' : 'bg-black text-gray-600 opacity-40 cursor-not-allowed'}`}
                  disabled={!affordable || buying === p.type} onClick={() => handlePurchase(p.type)}>
                  <div className="text-2xl mb-1">{p.icon}</div>
                  <div className="text-xs font-bold uppercase tracking-wider">{p.name}</div>
                  <div className="text-[10px] opacity-60 mt-0.5">{p.desc}</div>
                  <div className="text-[10px] mt-1 opacity-40 font-bold">{p.cost}</div>
                </button>
                {burstType === p.type && (
                  <div className="absolute inset-0 flex items-center justify-center pointer-events-none" aria-hidden="true">
                    <div className={`w-8 h-8 rounded-full border-2 ${p.color} powerup-burst`} />
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
