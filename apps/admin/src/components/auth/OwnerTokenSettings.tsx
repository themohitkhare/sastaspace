'use client';

import { useState } from 'react';
import { getOwnerToken, setOwnerToken, clearOwnerToken } from '@/hooks/useStdb';
import Icon from '@/components/Icon';

type Props = { open: boolean; onClose: () => void };

export default function OwnerTokenSettings({ open, onClose }: Props) {
  const [value, setValue] = useState(() => getOwnerToken() ?? '');
  const [saved, setSaved] = useState(false);

  if (!open) return null;

  const save = () => {
    if (!value.trim()) return;
    setOwnerToken(value.trim());
    setSaved(true);
    // Reload so the SastaspaceProvider rebuilds its connection with the token.
    setTimeout(() => {
      setSaved(false);
      onClose();
      window.location.reload();
    }, 600);
  };

  const clear = () => {
    clearOwnerToken();
    setValue('');
    window.location.reload();
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()} style={{ maxWidth: 560 }}>
        <div className="modal__title">SpacetimeDB owner token</div>
        <div className="modal__body">
          <p style={{ marginBottom: 12 }}>
            Paste the output of{' '}
            <code style={{ fontFamily: 'var(--font-mono)', background: 'var(--brand-paper)', padding: '1px 6px', borderRadius: 4, fontSize: 11 }}>
              spacetime login show --token
            </code>
            {' '}below. Stored only in this browser. Required for moderation actions and live log streaming.
          </p>
          <textarea
            className="input"
            style={{
              width: '100%',
              minHeight: 110,
              fontFamily: 'var(--font-mono)',
              fontSize: 11,
              resize: 'vertical',
              padding: 10,
              boxSizing: 'border-box',
            }}
            placeholder="eyJ0eXAiOiJKV1QiLCJhbGc..."
            value={value}
            onChange={e => setValue(e.target.value)}
            spellCheck={false}
            autoComplete="off"
          />
          {saved && (
            <div style={{ marginTop: 10, color: 'var(--brand-status-live)', fontSize: 13 }}>
              Saved — reloading…
            </div>
          )}
        </div>
        <div className="modal__actions">
          <button className="btn btn--ghost" onClick={clear} title="Forget the stored token">
            <Icon name="trash" size={13}/> Clear
          </button>
          <button className="btn btn--ghost" onClick={onClose}>Cancel</button>
          <button className="btn btn--approve" onClick={save} disabled={!value.trim() || saved}>
            <Icon name="check" size={13}/> Save
          </button>
        </div>
      </div>
    </div>
  );
}
