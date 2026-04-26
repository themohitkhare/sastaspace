'use client';

import { Suspense, useEffect } from 'react';
import { useSearchParams } from 'next/navigation';

function CallbackInner() {
  const params = useSearchParams();

  useEffect(() => {
    const token = params.get('token');
    if (token) {
      localStorage.setItem('admin_token', token);
    }
    window.location.replace('/');
  }, [params]);

  return null;
}

export default function AuthCallbackPage() {
  return (
    <div className="auth-shell">
      <div className="auth-card" style={{ textAlign: 'center', padding: '48px 32px' }}>
        <div className="auth-card__terminal" style={{ marginBottom: 18 }}>admin.sastaspace.com / auth / callback</div>
        <div className="spinner" style={{ marginBottom: 18 }}/>
        <div style={{ fontSize: 14, marginBottom: 4 }}>Verifying your link…</div>
        <div style={{ fontSize: 12, color: 'var(--color-fg-muted)', fontFamily: 'var(--font-mono)' }}>token=•••••• · email=•••••</div>
        <Suspense><CallbackInner/></Suspense>
      </div>
    </div>
  );
}
