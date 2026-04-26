'use client';

import Icon from '@/components/Icon';

type AuthDeniedProps = { email?: string; onSignOut: () => void };

export default function AuthDenied({ email, onSignOut }: AuthDeniedProps) {
  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span style={{ width: 26, height: 26, background: 'var(--brand-ink)', color: 'var(--brand-paper)', borderRadius: 6, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontWeight: 500, fontSize: 13 }}>s</span>
          <span style={{ fontSize: 16, fontWeight: 500, letterSpacing: '-0.01em' }}>sastaspace <span style={{ color: 'var(--color-fg-muted)', fontWeight: 400 }}>/ admin</span></span>
        </div>
        <div className="auth-card__terminal">admin.sastaspace.com —</div>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
          <span style={{ width: 32, height: 32, borderRadius: 8, background: 'var(--color-status-danger-bg)', color: 'var(--color-status-danger)', display: 'inline-flex', alignItems: 'center', justifyContent: 'center' }}>
            <Icon name="lock" size={16}/>
          </span>
        </div>
        <div className="auth-card__title">Access denied</div>
        <div className="auth-card__sub">This admin panel is owner-only. You're signed in as a different account.</div>

        {email && (
          <div style={{ background: 'var(--brand-paper)', border: '1px solid var(--color-border)', borderRadius: 8, padding: '12px 14px', marginBottom: 18 }}>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-fg-muted)', letterSpacing: '0.05em', marginBottom: 4 }}>signed in as</div>
            <div style={{ fontFamily: 'var(--font-mono)', fontSize: 13 }}>{email}</div>
          </div>
        )}

        <button className="btn auth-card__btn" onClick={onSignOut}>
          <Icon name="signout" size={14}/> Sign out
        </button>

        <div className="auth-card__sig">Built sasta. Shared openly. © Mohit Khare, 2026.</div>
      </div>
    </div>
  );
}
