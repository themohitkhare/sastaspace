'use client';

import { LEGIONS, REGIONS, ACTIVITY, ACTIVE_BATTLES, relTime } from '@/lib/data';

export default function TypeWars() {
  const totalDamage = LEGIONS.reduce((s, l) => s + l.damage, 0);
  const sortedLegions = [...LEGIONS].sort((a, b) => b.regions - a.regions);
  const legionById = Object.fromEntries(LEGIONS.map(l => [l.id, l]));

  return (
    <div>
      <div className="banner banner--success" style={{ background: 'var(--brand-ink)', color: 'var(--brand-paper)', borderColor: 'var(--brand-ink)' }}>
        <span style={{ width: 8, height: 8, borderRadius: '50%', background: 'var(--brand-status-live)', animation: 'live-pulse 2s ease-in-out infinite', display: 'inline-block' }}/>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 12 }}>WAR ACTIVE</span>
        <span>· started <strong>11h 06m</strong> ago · <strong>{ACTIVE_BATTLES.length}</strong> active battles · <strong>{(totalDamage / 1000).toFixed(1)}k</strong> total damage dealt</span>
      </div>

      <div className="split-3">
        <div>
          <div className="section__head"><h2 className="section__title">Legion standings</h2></div>
          <div className="card" style={{ padding: '4px 0' }}>
            <table className="legions-table">
              <thead><tr><th style={{ paddingLeft: 18 }}>Legion</th><th>Regions</th><th>Damage</th><th style={{ paddingRight: 18 }}>Players</th></tr></thead>
              <tbody>
                {sortedLegions.map(l => (
                  <tr key={l.id}>
                    <td style={{ paddingLeft: 18 }}>
                      <span className="legion-chip">
                        <span className="legion-swatch" style={{ background: l.color }}/>
                        {l.name}
                      </span>
                    </td>
                    <td className="mono" style={{ fontSize: 12 }}>{l.regions}</td>
                    <td className="mono" style={{ fontSize: 12 }}>{l.damage.toLocaleString()}</td>
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
              {REGIONS.map(r => {
                const l = legionById[r.legion];
                const hpPct = (r.hp / r.hpMax) * 100;
                const hpColor = hpPct > 60 ? 'var(--brand-status-live)' : hpPct > 30 ? 'var(--brand-sasta)' : '#b8412c';
                return (
                  <div key={r.name} className={`region-cell ${r.contested ? 'contested' : ''}`}>
                    <div className="region-cell__tint" style={{ background: l.color }}/>
                    <div className="region-cell__name">{r.name}</div>
                    <div className="region-cell__legion">{l.name.toLowerCase().replace(/\s+/g, '-')}</div>
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
          <div className="section__head"><h2 className="section__title">Live activity</h2></div>
          <div className="card" style={{ padding: 14 }}>
            <div className="activity-feed">
              {ACTIVITY.map((e, i) => {
                const l = legionById[e.legion];
                return (
                  <div key={i} className={`activity-item ${i === 0 ? 'activity-item--new' : ''}`} style={{ borderLeftColor: i === 0 ? l.color : undefined }}>
                    <span className="activity-item__time">{relTime(e.time)}</span>
                    {e.text}
                  </div>
                );
              })}
            </div>
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
            {ACTIVE_BATTLES.map((b, i) => {
              const l = legionById[b.legion];
              return (
                <tr key={i}>
                  <td style={{ paddingLeft: 18, fontWeight: 500, fontSize: 13 }}>{b.player}</td>
                  <td>
                    <span className="legion-chip">
                      <span className="legion-swatch" style={{ background: l.color }}/>
                      <span style={{ fontSize: 12 }}>{l.name}</span>
                    </span>
                  </td>
                  <td style={{ fontSize: 13 }}>{b.region}</td>
                  <td className="mono" style={{ fontSize: 12 }}>{b.startedMin}m ago</td>
                  <td className="mono" style={{ fontSize: 12 }}>{b.words}</td>
                  <td className="mono" style={{ fontSize: 12, paddingRight: 18 }}>{b.damage.toLocaleString()}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}
