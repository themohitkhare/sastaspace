'use client';
import { useMemo } from 'react';
import { useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/typewars-bindings';
import type { Region, Player, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  regions: Region[];
  player: Player;
  onBack: () => void;
}

interface PlayerEntry {
  username: string;
  legion: LegionId;
  seasonDamage: number;
  totalDamage: number;
  bestWpm: number;
}

export default function Leaderboard({ regions, player, onBack }: Props) {
  const [playerRows] = useTable(tables.player);

  const allPlayers: PlayerEntry[] = useMemo(() => (
    [...playerRows]
      .map(p => ({
        username: p.username,
        legion: p.legion as LegionId,
        seasonDamage: Number(p.seasonDamage),
        totalDamage: Number(p.totalDamage),
        bestWpm: p.bestWpm,
      }))
      .sort((a, b) => b.seasonDamage - a.seasonDamage)
  ), [playerRows]);

  const myRank = allPlayers.findIndex(p => p.username === player.username) + 1;

  // Legion standings: total damage across all regions (per-legion damage on each region row)
  const legionDmg: Record<LegionId, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };
  const legionRegions: Record<LegionId, number> = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0 };

  regions.forEach(r => {
    legionDmg[0] += r.damage_0;
    legionDmg[1] += r.damage_1;
    legionDmg[2] += r.damage_2;
    legionDmg[3] += r.damage_3;
    legionDmg[4] += r.damage_4;
    if (r.controlling_legion !== -1) {
      legionRegions[r.controlling_legion]++;
    }
  });

  const legionStandings = ([0, 1, 2, 3, 4] as LegionId[])
    .map(id => ({ id, dmg: legionDmg[id], regions: legionRegions[id], info: LEGION_INFO[id] }))
    .sort((a, b) => b.dmg - a.dmg);

  const maxLegionDmg = legionStandings[0]?.dmg ?? 1;
  const myLegion = LEGION_INFO[player.legion];
  const rosterLimit = 15;

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
        <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)', marginBottom: 8 }}>season 1</p>
        <h1 className="ss-h1">Leaderboard</h1>
        <p className="ss-lede" style={{ color: 'var(--brand-muted)', marginTop: 12 }}>
          Live standings across all 25 regions. Damage is the only currency.
        </p>

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
                    <span className="lb-dmg ss-mono">{l.dmg.toLocaleString()}</span>
                    <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>{l.regions} regions held</span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="lb-section">
          <div className="lb-section-head">
            <h2 className="ss-h3">Player Roster</h2>
            <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>top {Math.min(rosterLimit, allPlayers.length)} by season damage</span>
          </div>
          {allPlayers.length === 0 ? (
            <p className="ss-small" style={{ color: 'var(--brand-muted)' }}>no players registered yet — be the first to enlist.</p>
          ) : (
            <div className="lb-player-table">
              <div className="lb-thead">
                <span className="ss-label">#</span>
                <span className="ss-label">callsign</span>
                <span className="ss-label">legion</span>
                <span className="ss-label">best wpm</span>
                <span className="ss-label">season dmg</span>
              </div>
              {allPlayers.slice(0, rosterLimit).map((p, i) => {
                const isMe = p.username === player.username;
                const pInfo = LEGION_INFO[p.legion];
                return (
                  <div key={p.username} className={`lb-trow${isMe ? ' you' : ''}`}>
                    <span className="ss-mono" style={{ color: 'var(--brand-muted)' }}>{i + 1}</span>
                    <span style={{ fontWeight: isMe ? 600 : 400 }}>
                      {p.username}
                      {isMe && <span className="lb-you-tag">YOU</span>}
                    </span>
                    <div className="lb-leg-cell">
                      <div className="lb-legion-pip small" style={{ background: pInfo.color }} />
                      <span className="ss-small">{pInfo.name}</span>
                    </div>
                    <span className="ss-mono">{p.bestWpm}</span>
                    <span className="ss-mono">{p.seasonDamage.toLocaleString()}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="lb-section">
          <div className="lb-section-head">
            <h2 className="ss-h3">Your Records</h2>
            <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>
              {myRank > 0 ? `rank #${myRank}` : 'unranked'}
            </span>
          </div>
          <div className="personal-grid">
            {[
              { label: 'season rank', val: myRank > 0 ? `#${myRank}` : '—' },
              { label: 'total dmg', val: player.total_damage.toLocaleString() },
              { label: 'season dmg', val: player.season_damage.toLocaleString() },
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
