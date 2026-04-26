'use client';

import { useMemo } from 'react';
import { useSpacetimeDB, useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/typewars-bindings';
import { TypewarsProvider } from '@/hooks/useStdb';
import { relTime, LEGION_COLORS, LEGION_NAMES } from '@/lib/data';

function TypeWarsInner() {
  const { isActive } = useSpacetimeDB();
  const [playerRows] = useTable(tables.player);
  const [regionRows] = useTable(tables.region);
  const [battleRows] = useTable(tables.battle_session);
  const [warRows] = useTable(tables.global_war);
  const war = warRows[0];

  const legions = useMemo(() => {
    const map = new Map<number, { id: number; name: string; color: string; regions: number; damage: bigint; players: number }>();
    for (let i = 0; i <= 4; i++) {
      map.set(i, { id: i, name: LEGION_NAMES[i] ?? `Legion ${i}`, color: LEGION_COLORS[i] ?? '#888', regions: 0, damage: 0n, players: 0 });
    }
    for (const p of playerRows) {
      const l = map.get(p.legion);
      if (l) { l.players++; l.damage += p.seasonDamage; }
    }
    for (const r of regionRows) {
      if (r.controllingLegion >= 0) {
        const l = map.get(r.controllingLegion);
        if (l) l.regions++;
      }
    }
    return [...map.values()].filter(l => l.players > 0 || l.regions > 0).sort((a, b) => b.regions - a.regions);
  }, [playerRows, regionRows]);

  const totalDamage = useMemo(() => legions.reduce((s, l) => s + l.damage, 0n), [legions]);

  const activeBattles = useMemo(() => {
    return battleRows.filter(b => b.active).map(b => {
      const player = playerRows.find(p => p.identity.toHexString() === b.playerIdentity.toHexString());
      const region = regionRows.find(r => r.id === b.regionId);
      const legionId = player?.legion ?? 0;
      const startedAt = b.startedAt instanceof Date ? b.startedAt
        : typeof b.startedAt === 'bigint' ? new Date(Number(b.startedAt / 1000n)) : new Date(Number(b.startedAt));
      return {
        id: b.id,
        player: player?.username ?? 'unknown',
        legion: LEGION_NAMES[legionId] ?? `Legion ${legionId}`,
        legionColor: LEGION_COLORS[legionId] ?? '#888',
        region: region?.name ?? `Region ${b.regionId}`,
        startedAt: startedAt.toISOString(),
        words: b.wordsSpawned,
        damage: Number(b.damageDealt),
      };
    });
  }, [battleRows, playerRows, regionRows]);

  const warActive = activeBattles.length > 0 || playerRows.length > 0;
  const damageK = (Number(totalDamage) / 1000).toFixed(1);

  if (!isActive) {
    return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Connecting to SpacetimeDB…</div>;
  }

  if (legions.length === 0) {
    return <div className="card" style={{ padding: 40, textAlign: 'center', color: 'var(--color-fg-muted)' }}>No war data yet. Start a battle to see live stats.</div>;
  }

  return (
    <div>
      <div className="banner banner--success" style={{ background: warActive ? 'var(--brand-ink)' : 'var(--color-surface-2)', color: warActive ? 'var(--brand-paper)' : 'var(--color-fg-muted)', borderColor: warActive ? 'var(--brand-ink)' : 'var(--color-border)' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: warActive ? 'var(--brand-status-live)' : 'var(--brand-dust)', animation: warActive ? 'live-pulse 2s ease-in-out infinite' : 'none', display: 'inline-block' }}/>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>{warActive ? 'WAR ACTIVE' : 'WAR IDLE'}</span>
        {war && (
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, opacity: 0.8 }}>
            · season {war.season}
            {war.seasonStart && (
              <>
                {' · started '}
                {relTime(
                  war.seasonStart instanceof Date
                    ? war.seasonStart.toISOString()
                    : typeof war.seasonStart === 'bigint'
                    ? new Date(Number(war.seasonStart / 1000n)).toISOString()
                    : String(war.seasonStart),
                )}
              </>
            )}
            {' · '}
            <strong>{war.liberatedTerritories}</strong>/<strong>{war.enemyTerritories + war.liberatedTerritories}</strong> liberated
          </span>
        )}
        <span>· <strong>{activeBattles.length}</strong> active battles · <strong>{damageK}k</strong> total damage dealt · <strong>{playerRows.length}</strong> players</span>
      </div>

      <div className="split-3">
        <div>
          <div className="section__head"><h2 className="section__title">Legion standings</h2></div>
          <div className="card" style={{ padding: '4px 0' }}>
            <table className="legions-table">
              <thead><tr><th style={{ paddingLeft: 18 }}>Legion</th><th>Regions</th><th>Damage</th><th style={{ paddingRight: 18 }}>Players</th></tr></thead>
              <tbody>
                {legions.map(l => (
                  <tr key={l.id}>
                    <td style={{ paddingLeft: 18 }}>
                      <span className="legion-chip">
                        <span className="legion-swatch" style={{ background: l.color }}/>
                        {l.name}
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>{l.regions}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{Number(l.damage).toLocaleString()}</td>
                    <td className="mono" style={{ fontSize: 12, paddingRight: 18 }}>{l.players}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div>
          <div className="section__head"><h2 className="section__title">Region map</h2></div>
          <div className="card" style={{ padding: 14 }}>
            <div className="region-grid">
              {[...regionRows].sort((a, b) => a.id - b.id).map(r => {
                const controlling = r.controllingLegion >= 0 ? r.controllingLegion : -1;
                const color = controlling >= 0 ? (LEGION_COLORS[controlling] ?? '#888') : 'var(--brand-dust)';
                const legionName = controlling >= 0 ? (LEGION_NAMES[controlling] ?? `Legion ${controlling}`) : 'unclaimed';
                const hpPct = r.enemyMaxHp > 0n ? Number((r.enemyHp * 100n) / r.enemyMaxHp) : 0;
                const hpColor = hpPct > 60 ? 'var(--brand-status-live)' : hpPct > 30 ? 'var(--brand-sasta)' : '#b8412c';
                const contested = activeBattles.some(b => b.region === r.name);
                return (
                  <div key={r.id} className={`region-cell ${contested ? 'contested' : ''}`}>
                    <div className="region-cell__tint" style={{ background: color }}/>
                    <div className="region-cell__name">{r.name}</div>
                    <div className="region-cell__legion">{legionName.toLowerCase().replace(/\s+/g, '-')}</div>
                    <div className="region-cell__hp">
                      <div className="region-cell__hp-fill" style={{ width: `${hpPct}%`, background: hpColor }}/>
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        <div>
          <div className="section__head"><h2 className="section__title">Active battles</h2></div>
          <div className="card" style={{ padding: 14 }}>
            {activeBattles.length === 0 ? (
              <div style={{ color: 'var(--color-fg-muted)', fontSize: 13 }}>No active battles.</div>
            ) : (
              <div className="activity-feed">
                {activeBattles.map(b => (
                  <div key={String(b.id)} className="activity-item">
                    <span className="activity-item__time">{relTime(b.startedAt)}</span>
                    <span className="legion-chip" style={{ marginRight: 4 }}>
                      <span className="legion-swatch" style={{ background: b.legionColor }}/>
                    </span>
                    <strong>{b.player}</strong> in {b.region} · {b.words} words · {b.damage.toLocaleString()} dmg
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      <div style={{ height: 28 }}/>

      <div className="section__head"><h2 className="section__title">Active battles</h2></div>
      <div className="card" style={{ padding: '4px 0' }}>
        <table className="legions-table">
          <thead>
            <tr>
              <th style={{ paddingLeft: 18 }}>Player</th>
              <th>Legion</th>
              <th>Region</th>
              <th>Started</th>
              <th>Words</th>
              <th style={{ paddingRight: 18 }}>Damage</th>
            </tr>
          </thead>
          <tbody>
            {activeBattles.length === 0 ? (
              <tr><td colSpan={6} style={{ padding: '14px 18px', color: 'var(--color-fg-muted)', textAlign: 'center' }}>No active battles</td></tr>
            ) : activeBattles.map((b) => (
              <tr key={String(b.id)}>
                <td style={{ paddingLeft: 18, fontWeight: 500, fontSize: 13 }}>{b.player}</td>
                <td>
                  <span className="legion-chip">
                    <span className="legion-swatch" style={{ background: b.legionColor }}/>
                    <span style={{ fontSize: 12 }}>{b.legion}</span>
                  </span>
                </td>
                <td style={{ fontSize: 13 }}>{b.region}</td>
                <td className="mono" style={{ fontSize: 12 }}>{relTime(b.startedAt)}</td>
                <td className="mono" style={{ fontSize: 12 }}>{b.words}</td>
                <td className="mono" style={{ fontSize: 12, paddingRight: 18 }}>{b.damage.toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default function TypeWars() {
  return (
    <TypewarsProvider>
      <TypeWarsInner/>
    </TypewarsProvider>
  );
}
