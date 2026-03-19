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
    ]).then(([p, s]) => { setProfile(p); setShards(s); }).catch(() => setError(true));
  }, [playerId]);

  if (error) {
    return (<div data-testid="profile-error" role="alert" className="flex-1 flex items-center justify-center bg-black text-white"><div className="text-center"><p className="text-lg font-bold font-zero text-red-400">FAILED TO LOAD</p><button className="mt-3 px-4 py-2 border-brutal-sm font-zero font-bold text-sm bg-black text-white hover:bg-sasta-accent hover:text-black transition-colors" onClick={() => { setError(false); setProfile(null); setShards(null); }}>RETRY</button></div></div>);
  }
  if (!profile) {
    return <div data-testid="profile-loading" role="status" className="flex-1 flex items-center justify-center bg-black text-white"><p className="font-zero font-bold">LOADING...</p></div>;
  }

  const streakOnFire = profile.streak.count >= 3;

  return (
    <div data-testid="profile-page" className="flex-1 bg-black text-white p-3 overflow-y-auto">
      <h2 className="text-xl font-bold font-zero uppercase tracking-widest mb-4">PROFILE</h2>
      <div className={`border-brutal-sm p-3 mb-3 ${streakOnFire ? 'streak-fire' : ''}`} aria-label={`${profile.streak.count} day streak`}>
        <div className="flex items-center gap-2">
          <span className="text-2xl" aria-hidden="true">{'\u2726'}</span>
          <span className="text-4xl font-bold font-zero">{profile.streak.count}</span>
          <span className="text-xs font-zero opacity-60 uppercase tracking-wider">DAY STREAK</span>
        </div>
      </div>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="border-brutal-sm p-2" aria-label={`${profile.stages_completed} stages completed`}><div className="text-2xl font-bold font-zero">{profile.stages_completed}</div><div className="text-[10px] font-zero opacity-60 uppercase tracking-wider">STAGES</div></div>
        <div className="border-brutal-sm p-2" aria-label={`${profile.collection_pct}% collected`}><div className="text-2xl font-bold font-zero">{profile.collection_pct}%</div><div className="text-[10px] font-zero opacity-60 uppercase tracking-wider">COLLECTED</div></div>
        <div className="border-brutal-sm p-2" aria-label={`${profile.cards_shared} cards shared`}><div className="text-2xl font-bold font-zero">{profile.cards_shared}</div><div className="text-[10px] font-zero opacity-60 uppercase tracking-wider">SHARED</div></div>
        <div className="border-brutal-sm p-2" aria-label={`${profile.community_score} community impact`}><div className="text-2xl font-bold font-zero">{profile.community_score}</div><div className="text-[10px] font-zero opacity-60 uppercase tracking-wider">IMPACT</div></div>
      </div>
      {shards && (
        <div className="border-brutal-sm p-3 mb-3">
          <h3 className="text-[10px] font-bold font-zero opacity-60 uppercase tracking-widest mb-2">SHARDS</h3>
          <div className="grid grid-cols-5 gap-1 text-center">
            {SHARD_DISPLAY.map(({ key, icon, color }) => (
              <div key={key} className="border-brutal-sm p-1" aria-label={`${key}: ${shards[key]}`}>
                <div className={`text-lg ${color}`} aria-hidden="true">{icon}</div>
                <div className="text-xs font-bold font-zero">{shards[key]}</div>
              </div>
            ))}
          </div>
        </div>
      )}
      {profile.badges.length > 0 && (
        <div className="border-brutal-sm p-3">
          <h3 className="text-[10px] font-bold font-zero opacity-60 uppercase tracking-widest mb-2">BADGES</h3>
          <div className="flex gap-1.5 flex-wrap" role="list" aria-label="Earned badges">
            {profile.badges.map(badge => (<span key={badge} role="listitem" className="px-2 py-1 border-brutal-sm text-sasta-accent text-[10px] font-bold font-zero uppercase">{badge}</span>))}
          </div>
        </div>
      )}
    </div>
  );
}
