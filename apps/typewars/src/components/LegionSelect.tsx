'use client';
import { useState } from 'react';
import type { LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  onChoose: (legion: LegionId, username: string) => Promise<void>;
}

export default function LegionSelect({ onChoose }: Props) {
  const [picked, setPicked] = useState<LegionId | null>(null);
  const [callsign, setCallsign] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canEnlist = picked !== null && callsign.trim().length > 0 && !submitting;

  return (
    <div className="page">
      <header className="topbar">
        <span className="ss-mono" style={{ fontWeight: 600 }}>typewars.sastaspace.com</span>
        <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>— a sasta lab project</span>
        <span style={{ marginLeft: 'auto', color: 'var(--brand-muted)' }} className="ss-small ss-mono">season 1 · day 12 / 30</span>
      </header>

      <main className="ls-inner">
        <p className="ss-eyebrow ls-eyebrow">enlistment</p>
        <h1 className="ss-h1 ls-title">Choose your legion.</h1>
        <p className="ss-lede ls-lede">
          Every keystroke is an act of war. Select the faction whose doctrine matches your fighting style — you&apos;ll fight alongside thousands of others to liberate regions across the star map.
        </p>

        <div className="legion-grid">
          {([0, 1, 2, 3, 4] as LegionId[]).map((id) => {
            const info = LEGION_INFO[id];
            return (
              <button
                key={id}
                className={`legion-card${picked === id ? ' picked' : ''}`}
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
                <div className="legion-card-foot">
                  <span className="ss-small" style={{ color: 'var(--brand-muted)' }}>
                    {picked === id ? '✓ selected' : 'select'}
                  </span>
                </div>
              </button>
            );
          })}
        </div>

        <div className="ls-finalize">
          <div className="callsign-row">
            <label className="ss-label" style={{ color: 'var(--brand-muted)' }}>callsign</label>
            <input
              className="callsign-input"
              placeholder="enter your callsign"
              value={callsign}
              onChange={e => setCallsign(e.target.value)}
              maxLength={24}
            />
          </div>
          <button
            className="enlist-btn"
            disabled={!canEnlist}
            onClick={async () => {
              if (picked === null || !callsign.trim()) return;
              setSubmitting(true);
              setError(null);
              try {
                await onChoose(picked, callsign.trim());
              } catch (err) {
                setError(err instanceof Error ? err.message : 'enlistment failed');
                setSubmitting(false);
              }
            }}
          >
            {submitting ? 'enlisting…' : 'ENLIST →'}
          </button>
        </div>

        {error && (
          <p className="ss-small ls-warning" style={{ color: 'var(--brand-sasta-text)' }}>
            {error}
          </p>
        )}

        <p className="ss-small ls-warning">
          Legion allegiance is permanent for the season. Choose carefully — your mechanic will shape every battle you fight.
        </p>
      </main>

      <footer className="footer-sig">
        <span className="ss-small ss-mono">typewars · season 1 · a sasta lab project</span>
      </footer>
    </div>
  );
}
