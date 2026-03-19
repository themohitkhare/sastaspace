import React, { useEffect, useRef, useState } from 'react';
import useGameStore from '../store/useGameStore';

const SHARD_CONFIG = [
  { key: 'SOUL', label: 'SL', color: 'text-amber-500', icon: '\u2726' },
  { key: 'SHIELD', label: 'SH', color: 'text-blue-400', icon: '\u25C6' },
  { key: 'VOID', label: 'VD', color: 'text-red-500', icon: '\u2715' },
  { key: 'LIGHT', label: 'LT', color: 'text-yellow-400', icon: '\u2600' },
  { key: 'FORCE', label: 'FC', color: 'text-purple-500', icon: '\u2B1F' },
];

export default function ShardBar() {
  const shards = useGameStore((s) => s.shards);
  const prevShards = useRef(shards);
  const [bumping, setBumping] = useState({});

  useEffect(() => {
    const newBumps = {};
    SHARD_CONFIG.forEach(({ key }) => {
      if ((shards[key] || 0) > (prevShards.current[key] || 0)) {
        newBumps[key] = true;
      }
    });
    if (Object.keys(newBumps).length > 0) {
      setBumping(newBumps);
      const timer = setTimeout(() => setBumping({}), 250);
      prevShards.current = shards;
      return () => clearTimeout(timer);
    }
    prevShards.current = shards;
  }, [shards]);

  return (
    <div
      data-testid="shard-bar"
      role="status"
      aria-label="Shard balances"
      className="flex justify-between items-center px-2 py-1.5 bg-black border-b-2 border-sasta-accent"
    >
      {SHARD_CONFIG.map(({ key, label, color, icon }) => (
        <div
          key={key}
          className={`flex items-center gap-1 border-brutal-sm px-2 py-1 ${bumping[key] ? 'shard-bump' : ''}`}
          data-testid={`shard-${key}`}
          aria-label={`${label} shards: ${shards[key] || 0}`}
        >
          <span className={`${color} text-xs`} aria-hidden="true">{icon}</span>
          <span className="text-xs font-bold font-zero">{shards[key] || 0}</span>
        </div>
      ))}
    </div>
  );
}
