'use client';

import { useEffect, useRef } from 'react';

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (cfg: { client_id: string; callback: (r: { credential: string }) => void }) => void;
          renderButton: (el: HTMLElement, cfg: object) => void;
        };
      };
    };
  }
}

const CLIENT_ID = process.env.NEXT_PUBLIC_GOOGLE_CLIENT_ID ?? '';

type AuthSignInProps = { onSuccess: () => void };

export default function AuthSignIn({ onSuccess }: AuthSignInProps) {
  const btnRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function init() {
      if (!window.google?.accounts?.id || !btnRef.current) return;
      window.google.accounts.id.initialize({
        client_id: CLIENT_ID,
        callback(res) {
          localStorage.setItem('admin_token', res.credential);
          onSuccess();
        },
      });
      window.google.accounts.id.renderButton(btnRef.current, {
        theme: 'filled_black',
        size: 'large',
        text: 'signin_with',
        shape: 'rectangular',
        width: 280,
      });
    }

    if (window.google?.accounts?.id) {
      init();
      return;
    }
    const script = document.createElement('script');
    script.src = 'https://accounts.google.com/gsi/client';
    script.async = true;
    script.defer = true;
    script.onload = init;
    document.head.appendChild(script);
    return () => { script.onload = null; };
  }, [onSuccess]);

  return (
    <div className="auth-shell">
      <div className="auth-card">
        <div className="auth-card__brand">
          <span style={{ width: 26, height: 26, background: 'var(--brand-ink)', color: 'var(--brand-paper)', borderRadius: 6, display: 'inline-flex', alignItems: 'center', justifyContent: 'center', fontFamily: 'var(--font-mono)', fontWeight: 500, fontSize: 13 }}>s</span>
          <span style={{ fontSize: 16, fontWeight: 500, letterSpacing: '-0.01em' }}>sastaspace <span style={{ color: 'var(--color-fg-muted)', fontWeight: 400 }}>/ admin</span></span>
        </div>
        <div className="auth-card__terminal">admin.sastaspace.com —</div>
        <div className="auth-card__title">Sign in</div>
        <div className="auth-card__sub">Owner-only. Continue with your Google account.</div>

        <div ref={btnRef} style={{ margin: '20px 0', display: 'flex', justifyContent: 'center', minHeight: 44 }}/>

        <div className="auth-card__sig">Built sasta. Shared openly. © Mohit Khare, 2026.</div>
      </div>
    </div>
  );
}
