import React, { useEffect, useState } from 'react';
import useGameStore from '../store/useGameStore';

export default function ProfilePage() {
  const { playerId } = useGameStore();
  const [profile, setProfile] = useState(null);
  const [shards, setShards] = useState(null);

  useEffect(() => {
    Promise.all([
      fetch(`/api/v1/sastahero/profile?player_id=${playerId}`).then(r => r.json()),
      fetch(`/api/v1/sastahero/shards?player_id=${playerId}`).then(r => r.json()),
    ]).then(([p, s]) => {
      setProfile(p);
      setShards(s);
    }).catch(() => {});
  }, [playerId]);

  if (!profile) {
    return <div data-testid="profile-loading" className="flex-1 flex items-center justify-center bg-black text-white"><p>Loading...</p></div>;
  }

  return (
    <div data-testid="profile-page" className="flex-1 bg-black text-white p-4 overflow-y-auto">
      <h2 className="text-2xl font-bold mb-6">PROFILE</h2>

      {/* Streak */}
      <div className="border-2 border-white p-4 mb-4">
        <div className="flex items-center gap-2 mb-1">
          <span className="text-2xl">🔥</span>
          <span className="text-3xl font-bold">{profile.streak.count}</span>
          <span className="text-sm opacity-60">day streak</span>
        </div>
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 gap-3 mb-4">
        <div className="border-2 border-white p-3">
          <div className="text-2xl font-bold">{profile.stages_completed}</div>
          <div className="text-xs opacity-60">Stages</div>
        </div>
        <div className="border-2 border-white p-3">
          <div className="text-2xl font-bold">{profile.collection_pct}%</div>
          <div className="text-xs opacity-60">Collected</div>
        </div>
        <div className="border-2 border-white p-3">
          <div className="text-2xl font-bold">{profile.cards_shared}</div>
          <div className="text-xs opacity-60">Shared</div>
        </div>
        <div className="border-2 border-white p-3">
          <div className="text-2xl font-bold">{profile.community_score}</div>
          <div className="text-xs opacity-60">Impact</div>
        </div>
      </div>

      {/* Shards */}
      {shards && (
        <div className="border-2 border-white p-4 mb-4">
          <h3 className="text-sm font-bold mb-2 opacity-60">SHARDS</h3>
          <div className="grid grid-cols-5 gap-2 text-center">
            {[
              { key: 'SOUL', icon: '✦', color: 'text-amber-500' },
              { key: 'SHIELD', icon: '◆', color: 'text-blue-400' },
              { key: 'VOID', icon: '✕', color: 'text-red-500' },
              { key: 'LIGHT', icon: '☀', color: 'text-yellow-400' },
              { key: 'FORCE', icon: '⬟', color: 'text-purple-500' },
            ].map(({ key, icon, color }) => (
              <div key={key}>
                <div className={`text-xl ${color}`}>{icon}</div>
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
          <div className="flex gap-2 flex-wrap">
            {profile.badges.map(badge => (
              <span key={badge} className="px-2 py-1 border border-yellow-400 text-yellow-400 text-xs font-bold">
                {badge}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
