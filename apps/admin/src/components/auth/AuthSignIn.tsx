'use client';

import { useState } from 'react';
import Icon from '@/components/Icon';

type AuthSignInProps = { onSuccess: () => void };

export default function AuthSignIn({ onSuccess }: AuthSignInProps) {
  const [email, setEmail] = useState('');
  const [sent, setSent] = useState(false);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState('');

  const sendLink = async () => {
    setSending(true);
    setError('');
    try {
      const res = await fetch('https://auth.sastaspace.com/auth/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, callback: `${window.location.origin}/auth/callback` }),
      });
      if (res.ok) {
        setSent(true);
      } else {
        setError('Failed to send link. Try again.');
      }
    } catch {
      setError('Network error. Try again.');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span style={{ width: 26, height: 26, background: 'var(--brand-ink)', color: 'var(--brand-paper)', borderRadius: 6, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontWeight: 500, fontSize: 13 }}>s</span>
          <span style={{ fontSize: 16, fontWeight: 500, letterSpacing: '-0.01em' }}>sastaspace <span style={{ color: 'var(--color-fg-muted)', fontWeight: 400 }}>/ admin</span></span>
        </div>
        <div className="auth-card__terminal">admin.sastaspace.com —</div>
        <div className="auth-card__title">Sign in</div>
        <div className="auth-card__sub">Owner-only. Enter your email and we'll send a magic link.</div>

        {!sent ? (
          <>
            <div className="auth-card__field">
              <label>email</label>
              <input
                className="auth-card__input"
                type="email"
                placeholder="you@example.com"
                value={email}
                onChange={e => setEmail(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && email.includes('@') && sendLink()}
                autoFocus
              />
            </div>
            {error && <div style={{ fontSize: 13, color: '#b8412c', marginBottom: 10 }}>{error}</div>}
            <button className="btn btn--primary auth-card__btn" disabled={!email.includes('@') || sending} onClick={sendLink}>
              {sending ? <span className="spinner" style={{ width: 14, height: 14 }}/> : <Icon name="mail" size={14}/>}
              {sending ? 'Sending…' : 'Send magic link'}
            </button>
          </>
        ) : (
          <div style={{ padding: '14px 0', textAlign: 'center' }}>
            <div className="spinner" style={{ marginBottom: 14 }}/>
            <div style={{ fontSize: 14, marginBottom: 6 }}>Check your inbox.</div>
            <div style={{ fontSize: 13, color: 'var(--color-fg-muted)', marginBottom: 18 }}>
              We sent a link to <span className="mono">{email}</span>
            </div>
            <button className="btn btn--ghost btn--sm" onClick={() => { setSent(false); setEmail(''); }}>Try a different email</button>
          </div>
        )}

        <div className="auth-card__sig">Built sasta. Shared openly. © Mohit Khare, 2026.</div>
      </div>
    </div>
  );
}
