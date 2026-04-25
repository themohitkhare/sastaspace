'use client';
import type { Region, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  r: Region;
  onEnter: (r: Region) => void;
  onClose: () => void;
}

export default function RegionDetail({ r, onEnter, onClose }: Props) {
  const totalDamage = r.damage_0 + r.damage_1 + r.damage_2 + r.damage_3 + r.damage_4;
  const hpPct = (r.enemy_hp / r.enemy_max_hp) * 100;
  const isHeld = r.controlling_legion !== -1;
  const holder = isHeld ? LEGION_INFO[r.controlling_legion as LegionId] : null;

  const damages: Array<{ id: LegionId; dmg: number }> = ([0, 1, 2, 3, 4] as LegionId[]).map(id => ({
    id,
    dmg: r[`damage_${id}` as keyof Region] as number,
  })).filter(d => d.dmg > 0);

  const tierLabel = { 1: 'T1', 2: 'T2', 3: 'T3' }[r.tier];

  return (
    <div className="region-detail">
      <div className="rd-head">
        <div>
          <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)', marginBottom: 4 }}>
            region {String(r.id + 1).padStart(2, '0')} · {tierLabel}
          </p>
          <h2 className="ss-h3" style={{ margin: 0 }}>{r.name}</h2>
        </div>
        <button
          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--brand-muted)', fontSize: 18 }}
          onClick={onClose}
        >
          ×
        </button>
      </div>

      {isHeld && holder ? (
        <div className="rd-held" style={{ borderColor: holder.color, color: holder.color }}>
          <span className="player-dot" style={{ background: holder.color }} />
          <span className="ss-label">{holder.name} hold</span>
        </div>
      ) : (
        <div>
          <div className="rd-hp-row">
            <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>enemy HP</span>
            <span className="ss-mono ss-small">
              {r.enemy_hp.toLocaleString()} / {r.enemy_max_hp.toLocaleString()}
            </span>
          </div>
          <div className="hp-bar-outer" style={{ marginTop: 8 }}>
            <div className="hp-bar-inner" style={{ width: `${hpPct}%` }} />
          </div>
        </div>
      )}

      {damages.length > 0 && (
        <div className="rd-contrib">
          <p className="ss-small" style={{ color: 'var(--brand-muted)', marginBottom: 4 }}>damage dealt</p>
          {damages.map(({ id, dmg }) => {
            const info = LEGION_INFO[id];
            const pct = totalDamage > 0 ? (dmg / totalDamage) * 100 : 0;
            return (
              <div key={id} className="rd-contrib-row">
                <div className="rd-contrib-pip" style={{ background: info.color }} />
                <span className="ss-small">{info.name}</span>
                <div className="rd-contrib-bar">
                  <div className="rd-contrib-fill" style={{ width: `${pct}%`, background: info.color }} />
                </div>
                <span className="ss-mono ss-small" style={{ textAlign: 'right' }}>
                  {dmg.toLocaleString()}
                </span>
              </div>
            );
          })}
        </div>
      )}

      <div className="rd-meta">
        <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>
          {r.active_players} active · {r.active_wardens} wardens · regen {r.regen_rate}/s
        </span>
      </div>

      <button
        className="enlist-btn"
        style={{ width: '100%' }}
        onClick={() => onEnter(r)}
      >
        ENTER BATTLE →
      </button>
    </div>
  );
}
