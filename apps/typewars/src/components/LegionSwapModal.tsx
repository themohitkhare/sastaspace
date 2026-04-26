'use client';
import { useCallback, useEffect, useRef, useState } from 'react';
import type { Player, LegionId } from '@/types';
import { LEGION_INFO } from '@/lib/legions';

interface Props {
  player: Player;
  onClose: () => void;
  /** Returns a Promise — if it rejects, the modal stays open and surfaces the error. */
  onSwap: (legion: LegionId) => Promise<void>;
}

/**
 * Focus trap matching ProfileModal/SignInModal pattern (UX audit C2).
 * Auto-focuses first focusable element on mount, traps Tab/Shift+Tab.
 */
function useFocusTrap(containerRef: React.RefObject<HTMLElement | null>) {
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const firstFocusable = el.querySelector<HTMLElement>(
      'button, input, [href], select, textarea, [tabindex]:not([tabindex="-1"])',
    );
    firstFocusable?.focus();

    function onKeyDown(e: KeyboardEvent) {
      if (e.key !== 'Tab') return;
      const focusable = Array.from(
        el!.querySelectorAll<HTMLElement>(
          'button, input, [href], select, textarea, [tabindex]:not([tabindex="-1"])',
        ),
      ).filter((n) => !n.hasAttribute('disabled') && !n.closest('[aria-hidden]'));
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }

    el.addEventListener('keydown', onKeyDown);
    return () => el.removeEventListener('keydown', onKeyDown);
  }, [containerRef]);
}

export default function LegionSwapModal({ player, onClose, onSwap }: Props) {
  const [picked, setPicked] = useState<LegionId>(player.legion);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const dialogRef = useRef<HTMLDivElement | null>(null);

  useFocusTrap(dialogRef);

  // Esc closes modal (matches AuthMenu/ProfileModal/SignInModal)
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape' && !loading) onClose();
    },
    [onClose, loading],
  );

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  const handleConfirm = async () => {
    if (picked === player.legion || loading) return;
    setLoading(true);
    setError(null);
    try {
      await onSwap(picked);
      // onSwap is responsible for closing the modal on success
    } catch (e) {
      setError(e instanceof Error ? e.message : 'swap failed — please try again');
      setLoading(false);
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onClick={onClose}>
      <div
        className="modal"
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Switch legion"
        onClick={e => e.stopPropagation()}
      >
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

        {error && (
          <p className="ss-small" style={{ color: 'var(--brand-sasta-text)', marginTop: 10 }}>
            {error}
          </p>
        )}

        <div className="legion-grid" style={{ marginTop: 24 }}>
          {([0, 1, 2, 3, 4] as LegionId[]).map((id) => {
            const info = LEGION_INFO[id];
            const isCurrent = id === player.legion;
            return (
              <button
                key={id}
                className={`legion-card${picked === id ? ' picked' : ''}${isCurrent ? ' current' : ''}`}
                style={{ ['--lc' as string]: info.color }}
                onClick={() => !loading && setPicked(id)}
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
          <button className="link-btn" onClick={onClose} disabled={loading}>cancel</button>
          <button
            className="enlist-btn"
            disabled={picked === player.legion || loading}
            onClick={handleConfirm}
          >
            {loading ? 'switching…' : 'Confirm switch →'}
          </button>
        </div>
      </div>
    </div>
  );
}
