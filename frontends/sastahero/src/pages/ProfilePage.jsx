import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

const SHARD_DISPLAY = [
  { key: 'SOUL', icon: '\u2726', color: 'text-amber-500' },
  { key: 'SHIELD', icon: '\u25C6', color: 'text-blue-400' },
  { key: 'VOID', icon: '\u2715', color: 'text-red-500' },
  { key: 'LIGHT', icon: '\u2600', color: 'text-yellow-400' },
  { key: 'FORCE', icon: '\u2B1F', color: 'text-purple-500' },
];

export default function ProfilePage() {
  const { playerId } = useGameStore();
  const [profile, setProfile] = useState(null);
  const [shards, setShards] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    Promise.all([
      fetch(`/api/v1/sastahero/profile?player_id=${playerId}`).then(r => r.json()),
      fetch(`/api/v1/sastahero/shards?player_id=${playerId}`).then(r => r.json()),
    ]).then(([p, s]) => {
      setProfile(p);
      setShards(s);
    }).catch(() => setError(true));
  }, [playerId]);

  if (error) {
    return (
      <div data-testid="profile-error" role="alert" className="flex-1 flex items-center justify-center bg-black text-white">
        <div className="text-center">
          <p className="text-lg font-bold text-red-400">Failed to load profile</p>
          <button className="mt-3 px-4 py-2 border-2 border-white text-sm" onClick={() => { setError(false); setProfile(null); setShards(null); }}>Retry</button>
        </div>
      </div>
    );
  }

  if (!profile) {
    return <div data-testid="profile-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white"><p>Loading...</p></div>;
  }

  return (
    <div data-testid="profile-page" className="flex-1 bg-black text-white p-4 overflow-y-auto">
      <h2 className="text-2xl font-bold mb-6">PROFILE</h2>

      {/* Streak */}
      <div className="border-2 border-white p-4 mb-4" aria-label={`${profile.streak.count} day streak`}>
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl" aria-hidden="true">{'\u2726'}</span>
          <span className="text-3xl font-bold">{profile.streak.count}</span>
          <span className="text-sm opacity-60">day streak</span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="border-2 border-white p-3" aria-label={`${profile.stages_completed} stages completed`}>
          <div className="text-2xl font-bold">{profile.stages_completed}</div>
          <div className="text-xs opacity-60">Stages</div>
        </div>
        <div className="border-2 border-white p-3" aria-label={`${profile.collection_pct}% collected`}>
          <div className="text-2xl font-bold">{profile.collection_pct}%</div>
          <div className="text-xs opacity-60">Collected</div>
        </div>
        <div className="border-2 border-white p-3" aria-label={`${profile.cards_shared} cards shared`}>
          <div className="text-2xl font-bold">{profile.cards_shared}</div>
          <div className="text-xs opacity-60">Shared</div>
        </div>
        <div className="border-2 border-white p-3" aria-label={`${profile.community_score} community impact`}>
          <div className="text-2xl font-bold">{profile.community_score}</div>
          <div className="text-xs opacity-60">Impact</div>
        </div>
      </div>

      {/* Shards */}
      {shards && (
        <div className="border-2 border-white p-4 mb-4">
          <h3 className="text-sm font-bold mb-2 opacity-60">SHARDS</h3>
          <div className="grid grid-cols-5 gap-2 text-center">
            {SHARD_DISPLAY.map(({ key, icon, color }) => (
              <div key={key} aria-label={`${key}: ${shards[key]}`}>
                <div className={`text-xl ${color}`} aria-hidden="true">{icon}</div>
                <div className="text-sm font-bold">{shards[key]}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Badges */}
      {profile.badges.length > 0 && (
        <div className="border-2 border-white p-4">
          <h3 className="text-sm font-bold mb-2 opacity-60">BADGES</h3>
          <div className="flex gap-2 flex-wrap" role="list" aria-label="Earned badges">
            {profile.badges.map(badge => (
              <span key={badge} role="listitem" className="px-2 py-1 border border-yellow-400 text-yellow-400 text-xs font-bold">
                {badge}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
