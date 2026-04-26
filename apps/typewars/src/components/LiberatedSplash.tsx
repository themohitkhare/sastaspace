'use client';
import type { Region, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  region: Region;
  winner: LegionId;
  onContinue: () => void;
}

export default function LiberatedSplash({ region, winner, onContinue }: Props) {
  const winnerInfo = LEGION_INFO[winner];
  const tierLabel = { 1: 'tier 1', 2: 'tier 2', 3: 'tier 3' }[region.tier];

  const legionDamages = ([0, 1, 2, 3, 4] as LegionId[])
    .map(id => ({ id, dmg: region[`damage_${id}` as keyof Region] as number, info: LEGION_INFO[id] }))
    .sort((a, b) => b.dmg - a.dmg);

  const totalDmg = legionDamages.reduce((s, l) => s + l.dmg, 0);

  return (
    <div className="liberated">
      <div className="lib-inner">
        <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)' }}>region liberated</p>
        <div className="lib-tag" style={{ borderColor: winnerInfo.color, color: winnerInfo.color }}>
          <span className="lib-tag-dot" style={{ background: winnerInfo.color }} />
          <span className="ss-label">{winnerInfo.name} · {winnerInfo.mechanic}</span>
        </div>
        <h1 className="ss-h1 lib-title">{region.name}</h1>
        <p className="ss-lede" style={{ color: 'var(--brand-muted)', marginTop: 12 }}>
          The {region.name} has been liberated. {winnerInfo.name} forces dealt the most damage and now hold the region. {tierLabel} regen is suppressed.
        </p>

        <div className="lib-grid">
          <div className="lib-block">
            <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)' }}>battle stats</p>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 12, marginTop: 12 }}>
              <div>
                <p className="ss-small" style={{ color: 'var(--brand-muted)', marginBottom: 2 }}>total damage dealt</p>
                <p className="ss-h3 ss-mono" style={{ margin: 0 }}>{totalDmg.toLocaleString()}</p>
              </div>
              <div>
                <p className="ss-small" style={{ color: 'var(--brand-muted)', marginBottom: 2 }}>region tier</p>
                <p className="ss-h3" style={{ margin: 0, color: winnerInfo.color }}>T{region.tier}</p>
              </div>
              <div>
                <p className="ss-small" style={{ color: 'var(--brand-muted)', marginBottom: 2 }}>controlling legion</p>
                <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
                  <span style={{ width: 10, height: 10, borderRadius: 2, background: winnerInfo.color, display: 'inline-block' }} />
                  <span className="ss-body">{winnerInfo.name}</span>
                </div>
              </div>
            </div>
          </div>

          <div className="lib-block">
            <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)' }}>legion contribution</p>
            <ul className="lib-contrib-list">
              {legionDamages.map((l, i) => (
                <li key={l.id}>
                  <span className="lib-rank">{i + 1}</span>
                  <span className="lib-name">{l.info.name}</span>
                  <span className="lib-leg-pip" style={{ background: l.info.color }} />
                  <span className="lib-dmg ss-mono">{l.dmg.toLocaleString()}</span>
                </li>
              ))}
            </ul>
          </div>
        </div>

        <div style={{ display: 'flex', gap: 16, alignItems: 'center' }}>
          <button className="enlist-btn" onClick={onContinue}>
            RETURN TO MAP →
          </button>
          <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>
            The war continues across 25 worlds.
          </span>
        </div>
      </div>
    </div>
  );
}
