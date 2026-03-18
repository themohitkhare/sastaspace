import React from 'react';
import useGameStore from '../store/useGameStore';

const SHARD_CONFIG = [
  { key: 'SOUL', label: 'Soul', color: 'text-amber-500', icon: '\u2726' },
  { key: 'SHIELD', label: 'Shield', color: 'text-blue-400', icon: '\u25C6' },
  { key: 'VOID', label: 'Void', color: 'text-red-500', icon: '\u2715' },
  { key: 'LIGHT', label: 'Light', color: 'text-yellow-400', icon: '\u2600' },
  { key: 'FORCE', label: 'Force', color: 'text-purple-500', icon: '\u2B1F' },
];

export default function ShardBar() {
  const shards = useGameStore((s) => s.shards);

  return (
    <div
      data-testid="shard-bar"
      role="status"
      aria-label="Shard balances"
      className="flex justify-between items-center px-3 py-2 bg-black text-white border-b-2 border-sasta-black"
    >
      {SHARD_CONFIG.map(({ key, label, color, icon }) => (
        <div
          key={key}
          className="flex items-center gap-1"
          data-testid={`shard-${key}`}
          aria-label={`${label} shards: ${shards[key] || 0}`}
        >
          <span className={`${color} text-sm`} aria-hidden="true">{icon}</span>
          <span className="text-xs font-bold">{shards[key] || 0}</span>
        </div>
      ))}
    </div>
  );
}
