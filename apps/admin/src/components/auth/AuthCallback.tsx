export default function AuthCallback() {
  return (
    <div className="auth-shell">
      <div className="auth-card" style={{ textAlign: 'center', padding: '48px 32px' }}>
        <div className="auth-card__terminal" style={{ marginBottom: 18 }}>admin.sastaspace.com / auth / callback</div>
        <div className="spinner" style={{ marginBottom: 18 }}/>
        <div style={{ fontSize: 14, marginBottom: 4 }}>Verifying your link…</div>
        <div style={{ fontSize: 12, color: 'var(--color-fg-muted)', fontFamily: 'var(--font-mono)' }}>token=•••••• · email=•••••</div>
      </div>
    </div>
  );
}
