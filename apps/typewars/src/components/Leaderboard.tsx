'use client';
import type { Region, Player, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  regions: Region[];
  player: Player;
  onBack: () => void;
}

interface FakePlayer {
  name: string;
  legion: LegionId;
  damage: number;
  wpm: number;
  sessions: number;
}

const FAKE_PLAYERS: FakePlayer[] = [
  { name: 'vex_prime',     legion: 0, damage: 2840000, wpm: 112, sessions: 47 },
  { name: 'null_void',     legion: 3, damage: 2710000, wpm: 98,  sessions: 52 },
  { name: 'cipher_9',     legion: 1, damage: 2560000, wpm: 135, sessions: 38 },
  { name: 'ashrun',       legion: 0, damage: 2390000, wpm: 88,  sessions: 61 },
  { name: 'orb_warden',   legion: 2, damage: 2210000, wpm: 76,  sessions: 74 },
  { name: 'quasar_k',     legion: 4, damage: 2100000, wpm: 101, sessions: 41 },
  { name: 'nova_burst',   legion: 0, damage: 1980000, wpm: 94,  sessions: 35 },
  { name: 'surge_x',      legion: 3, damage: 1850000, wpm: 89,  sessions: 29 },
  { name: 'helm_deep',    legion: 2, damage: 1730000, wpm: 72,  sessions: 88 },
  { name: 'ember_sol',    legion: 4, damage: 1620000, wpm: 83,  sessions: 44 },
  { name: 'rift_walker',  legion: 1, damage: 1540000, wpm: 128, sessions: 22 },
  { name: 'tarn_echo',    legion: 2, damage: 1450000, wpm: 68,  sessions: 95 },
  { name: 'verity_arc',   legion: 1, damage: 1380000, wpm: 117, sessions: 31 },
  { name: 'dust_herald',  legion: 4, damage: 1290000, wpm: 79,  sessions: 57 },
  { name: 'iron_surge',   legion: 3, damage: 1210000, wpm: 92,  sessions: 33 },
];

export default function Leaderboard({ regions, player, onBack }: Props) {
  // Insert real player
  const myEntry: FakePlayer = {
    name: player.username,
    legion: player.legion,
    damage: player.total_damage,
    wpm: player.best_wpm,
    sessions: 1,
  };

  const allPlayers = [...FAKE_PLAYERS, myEntry].sort((a, b) => b.damage - a.damage);
  const myRank = allPlayers.findIndex(p => p.name === player.username) + 1;

  // Legion standings
  const legionDmg: Record<LegionId, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };
  const legionRegions: Record<LegionId, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };

  allPlayers.forEach(p => {
    legionDmg[p.legion] += p.damage;
  });
  regions.forEach(r => {
    if (r.controlling_legion !== -1) {
      legionRegions[r.controlling_legion]++;
    }
  });

  const legionStandings = ([0, 1, 2, 3, 4] as LegionId[])
    .map(id => ({ id, dmg: legionDmg[id], regions: legionRegions[id], info: LEGION_INFO[id] }))
    .sort((a, b) => b.dmg - a.dmg);

  const maxLegionDmg = legionStandings[0]?.dmg ?? 1;
  const myLegion = LEGION_INFO[player.legion];

  return (
    <div className="page" style={{ background: 'var(--brand-paper)' }}>
      <header className="topbar">
        <button className="link-btn" onClick={onBack}>← war map</button>
        <span className="ss-mono" style={{ fontWeight: 600, marginLeft: 8 }}>typewars.sastaspace.com</span>
        <span style={{ marginLeft: 'auto' }}>
          <div className="player-pill">
            <span className="player-dot" style={{ background: myLegion.color }} />
            <span className="ss-label">{player.username}</span>
          </div>
        </span>
      </header>

      <main className="lb-inner">
        <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)', marginBottom: 8 }}>season 1 · day 12 / 30</p>
        <h1 className="ss-h1">Leaderboard</h1>
        <p className="ss-lede" style={{ color: 'var(--brand-muted)', marginTop: 12 }}>
          Current standings across all 25 regions. Rankings update in real time.
        </p>

        {/* Legion standings */}
        <div className="lb-section">
          <div className="lb-section-head">
            <h2 className="ss-h3">Legion Standings</h2>
            <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>by total damage</span>
          </div>
          <div className="lb-legion-list">
            {legionStandings.map((l, i) => {
              const pct = maxLegionDmg > 0 ? (l.dmg / maxLegionDmg) * 100 : 0;
              return (
                <div key={l.id} className="lb-legion-row">
                  <span className="lb-rank">{i + 1}</span>
                  <div>
                    <div className="lb-legion-name-row">
                      <div className="lb-legion-pip" style={{ background: l.info.color }} />
                      <span className="lb-legion-name">{l.info.name}</span>
                      <span className="ss-label ss-mono" style={{ color: 'var(--brand-muted)', marginLeft: 6 }}>{l.info.short}</span>
                    </div>
                    <div className="lb-bar">
                      <div className="lb-bar-fill" style={{ width: `${pct}%`, background: l.info.color }} />
                    </div>
                  </div>
                  <div className="lb-legion-nums">
                    <span className="lb-dmg ss-mono">{(l.dmg / 1e6).toFixed(2)}M</span>
                    <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>{l.regions} regions held</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Player roster */}
        <div className="lb-section">
          <div className="lb-section-head">
            <h2 className="ss-h3">Player Roster</h2>
            <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>top {allPlayers.length} by season damage</span>
          </div>
          <div className="lb-player-table">
            <div className="lb-thead">
              <span className="ss-label">#</span>
              <span className="ss-label">callsign</span>
              <span className="ss-label">legion</span>
              <span className="ss-label">best wpm</span>
              <span className="ss-label">season dmg</span>
            </div>
            {allPlayers.map((p, i) => {
              const isMe = p.name === player.username;
              const pInfo = LEGION_INFO[p.legion];
              return (
                <div key={i} className={`lb-trow${isMe ? ' you' : ''}`}>
                  <span className="ss-mono" style={{ color: 'var(--brand-muted)' }}>{i + 1}</span>
                  <span style={{ fontWeight: isMe ? 600 : 400 }}>
                    {p.name}
                    {isMe && <span className="lb-you-tag">YOU</span>}
                  </span>
                  <div className="lb-leg-cell">
                    <div className="lb-legion-pip small" style={{ background: pInfo.color }} />
                    <span className="ss-small">{pInfo.name}</span>
                  </div>
                  <span className="ss-mono">{p.wpm}</span>
                  <span className="ss-mono">{p.damage.toLocaleString()}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Personal records */}
        <div className="lb-section">
          <div className="lb-section-head">
            <h2 className="ss-h3">Your Records</h2>
            <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>rank #{myRank}</span>
          </div>
          <div className="personal-grid">
            {[
              { label: 'season rank', val: `#${myRank}` },
              { label: 'total dmg', val: player.total_damage.toLocaleString() },
              { label: 'best wpm', val: String(player.best_wpm) },
              { label: 'legion', val: myLegion.name },
              { label: 'mechanic', val: myLegion.mechanic },
            ].map(({ label, val }) => (
              <div key={label} className="hud-stat">
                <span className="hud-label">{label}</span>
                <span className="hud-val">{val}</span>
              </div>
            ))}
          </div>
        </div>
      </main>

      <footer className="footer-sig">
        <span className="ss-small ss-mono">typewars · season 1 · a sasta lab project</span>
      </footer>
    </div>
  );
}
