'use client';
import { useState } from 'react';
import type { Player, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  player: Player;
  onClose: () => void;
  onSwap: (legion: LegionId) => void;
}

export default function LegionSwapModal({ player, onClose, onSwap }: Props) {
  const [picked, setPicked] = useState<LegionId>(player.legion);

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-head">
          <div>
            <p className="ss-eyebrow" style={{ color: 'var(--brand-muted)', marginBottom: 6 }}>change allegiance</p>
            <h2 className="ss-h2" style={{ margin: 0 }}>Switch Legion</h2>
          </div>
          <button
            style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--brand-muted)', fontSize: 24 }}
            onClick={onClose}
          >
            ×
          </button>
        </div>

        <p className="ss-body" style={{ color: 'var(--brand-muted)', marginTop: 12 }}>
          You can switch legions at any time. Your damage history stays with you.
        </p>

        <div className="legion-grid" style={{ marginTop: 24 }}>
          {([0, 1, 2, 3, 4] as LegionId[]).map((id) => {
            const info = LEGION_INFO[id];
            const isCurrent = id === player.legion;
            return (
              <button
                key={id}
                className={`legion-card${picked === id ? ' picked' : ''}${isCurrent ? ' current' : ''}`}
                style={{ ['--lc' as string]: info.color }}
                onClick={() => setPicked(id)}
              >
                <div className="legion-card-top">
                  <span className="ss-label legion-num">0{id + 1}</span>
                  <span className="legion-tag" style={{ background: info.color }}>{info.short}</span>
                </div>
                <h3 className="ss-h3 legion-name">{info.name}</h3>
                <span className="legion-mech ss-label">{info.mechanic}</span>
                <p className="ss-small legion-text">{info.text}</p>
                {isCurrent && (
                  <div className="legion-card-foot">
                    <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>current</span>
                  </div>
                )}
              </button>
            );
          })}
        </div>

        <div className="modal-foot">
          <button className="link-btn" onClick={onClose}>cancel</button>
          <button
            className="enlist-btn"
            disabled={picked === player.legion}
            onClick={() => onSwap(picked)}
          >
            CONFIRM SWITCH →
          </button>
        </div>
      </div>
    </div>
  );
}
