'use client';

import { useMemo, useState, useEffect } from 'react';
import { useSpacetimeDB, useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/stdb-bindings';
import { usePoll } from '@/hooks/usePoll';
import Icon from '@/components/Icon';
import Dashboard from '@/components/panels/Dashboard';
import Comments from '@/components/panels/Comments';
import Server from '@/components/panels/Server';
import Services from '@/components/panels/Services';
import TypeWars from '@/components/panels/TypeWars';
import Logs from '@/components/panels/Logs';
import AuthSignIn from '@/components/auth/AuthSignIn';
import AuthDenied from '@/components/auth/AuthDenied';
import OwnerTokenSettings from '@/components/auth/OwnerTokenSettings';
import { USE_STDB_ADMIN, useOwnerToken } from '@/hooks/useStdb';
import type { ContainerRow } from '@/lib/types';

const OWNER_EMAIL = process.env.NEXT_PUBLIC_OWNER_EMAIL ?? '';

const NAV_ITEMS = [
  { id: 'dashboard', path: '/', label: 'Dashboard', icon: 'dashboard' },
  { id: 'comments', path: '/comments', label: 'Comments', icon: 'comments' },
  { id: 'server', path: '/server', label: 'Server', icon: 'server' },
  { id: 'services', path: '/services', label: 'Services', icon: 'services' },
  { id: 'game', path: '/game', label: 'TypeWars', icon: 'game' },
  { id: 'logs', path: '/logs', label: 'Logs', icon: 'logs' },
];

const PAGE_TITLES: Record<string, string> = {
  '/': 'Dashboard',
  '/comments': 'Comments',
  '/server': 'Server',
  '/services': 'Services',
  '/game': 'TypeWars',
  '/logs': 'Logs',
};

type Route = { path: string; params: URLSearchParams };

function parsePath(): Route {
  if (typeof window === 'undefined') return { path: '/', params: new URLSearchParams() };
  const hash = window.location.hash.slice(1) || '/';
  const [path, query] = hash.split('?');
  return { path: path || '/', params: new URLSearchParams(query ?? '') };
}

type AuthState = 'loading' | 'signin' | 'denied' | 'app';

function readToken(): { email: string } | null {
  try {
    const raw = localStorage.getItem('admin_token');
    if (!raw) return null;
    const payload = JSON.parse(atob(raw.split('.')[1]));
    if (payload.exp && payload.exp < Date.now() / 1000) return null;
    return { email: payload.email ?? payload.sub ?? '' };
  } catch {
    return null;
  }
}

function resolveAuth(): { state: AuthState; email: string } {
  if (typeof window === 'undefined') return { state: 'loading', email: '' };
  const token = readToken();
  if (!token) return { state: 'signin', email: '' };
  const state = OWNER_EMAIL && token.email !== OWNER_EMAIL ? 'denied' : 'app';
  return { state, email: token.email };
}

export default function Shell() {
  const [route, setRoute] = useState<Route>(() => parsePath());
  const [authState, setAuthState] = useState<AuthState>(() => resolveAuth().state);
  const [userEmail, setUserEmail] = useState<string>(() => resolveAuth().email);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [secondsSince, setSecondsSince] = useState(0);
  const [refreshing, setRefreshing] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const ownerToken = useOwnerToken();

  // Live data for nav badges
  const { isActive } = useSpacetimeDB();
  const [commentRows] = useTable(tables.comment);
  // Containers source: STDB table when flag on, /containers HTTP poll when off
  const [containerStatusRows] = useTable(tables.container_status);
  const { data: containersPolled } = usePoll<ContainerRow[]>(
    USE_STDB_ADMIN ? '__skip__' : '/containers',
    30000,
  );
  const containers: ContainerRow[] | null = USE_STDB_ADMIN
    ? containerStatusRows.map(r => ({
        name: r.name,
        status: r.status,
        image: r.image,
        started_at: '',
        uptime_s: Number(r.uptimeS),
        mem_usage_mb: r.memUsedMb,
        mem_limit_mb: r.memLimitMb,
        restart_count: r.restartCount,
      }))
    : (containersPolled ?? null);

  // Hash routing — only register the listener, initial state is set via lazy initializer
  useEffect(() => {
    const onHash = () => setRoute(parsePath());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // "Updated X seconds ago" counter
  useEffect(() => {
    const id = setInterval(() => setSecondsSince(s => s + 1), 1000);
    return () => clearInterval(id);
  }, []);

  const navigate = (p: string) => { window.location.hash = p; };

  const refresh = () => {
    setRefreshing(true);
    setTimeout(() => { setRefreshing(false); setSecondsSince(0); }, 600);
  };

  const signOut = () => {
    localStorage.removeItem('admin_token');
    setAuthState('signin');
    setUserEmail('');
  };

  const onSignInSuccess = () => {
    const { state, email } = resolveAuth();
    setUserEmail(email);
    setAuthState(state);
  };

  // Hooks must run unconditionally — derive nav-badge values before the
  // auth gate early-returns below.
  const pendingCount = useMemo(
    () => isActive ? commentRows.filter(c => c.status === 'pending' || c.status === 'flagged').length : 0,
    [isActive, commentRows],
  );
  const anyDown = useMemo(
    () => containers ? containers.some(c => c.status !== 'running') : false,
    [containers],
  );

  if (authState === 'loading') {
    return <div className="auth-shell"><div className="spinner"/></div>;
  }

  if (authState === 'signin') {
    return <AuthSignIn onSuccess={onSignInSuccess}/>;
  }

  if (authState === 'denied') {
    return <AuthDenied email={userEmail} onSignOut={signOut}/>;
  }

  const isLogs = route.path === '/logs';

  let panel: React.ReactNode;
  switch (route.path) {
    case '/': panel = <Dashboard navigate={navigate}/>; break;
    case '/comments': panel = <Comments initialFilter={route.params.get('status') ?? 'pending'}/>; break;
    case '/server': panel = <Server/>; break;
    case '/services': panel = <Services navigate={navigate}/>; break;
    case '/game': panel = <TypeWars/>; break;
    case '/logs': panel = <Logs initialService={route.params.get('service') ?? undefined}/>; break;
    default: panel = <div style={{ padding: 40, color: 'var(--color-fg-muted)' }}>Page not found.</div>;
  }

  return (
    <div className={`app ${sidebarCollapsed ? 'collapsed' : ''}`}>
      <aside className={`sidebar ${sidebarCollapsed ? 'collapsed' : ''}`}>
        <div className="sidebar__brand">
          <span className="sidebar__logo">s</span>
          {!sidebarCollapsed && <span className="sidebar__name">sastaspace <span className="dim">/ admin</span></span>}
          {!sidebarCollapsed && (
            <button className="sidebar__collapse" onClick={() => setSidebarCollapsed(true)} title="Collapse">
              <Icon name="collapse" size={14}/>
            </button>
          )}
        </div>
        {sidebarCollapsed && (
          <button className="sidebar__collapse" style={{ alignSelf: 'center', marginTop: 8 }} onClick={() => setSidebarCollapsed(false)} title="Expand">
            <Icon name="expand" size={14}/>
          </button>
        )}
        <nav className="sidebar__nav">
          {NAV_ITEMS.map(it => {
            const active = route.path === it.path;
            return (
              <button key={it.id} className={`nav__item ${active ? 'active' : ''}`} onClick={() => navigate(it.path)} title={sidebarCollapsed ? it.label : undefined}>
                <span className="nav__icon" style={{ display: 'inline-flex' }}><Icon name={it.icon} size={18}/></span>
                <span className="nav__label">{it.label}</span>
                {it.id === 'comments' && pendingCount > 0 && <span className="nav__badge">{pendingCount}</span>}
                {it.id === 'services' && anyDown && <span className="nav__dot"/>}
              </button>
            );
          })}
        </nav>
        <div className="sidebar__footer">
          {!sidebarCollapsed && <div className="footer__email">{userEmail || OWNER_EMAIL || 'admin'}</div>}
          {USE_STDB_ADMIN && (
            <button
              className="footer__signout"
              onClick={() => setSettingsOpen(true)}
              title={ownerToken ? 'Owner STDB token: configured' : 'Owner STDB token: not set — paste to enable moderation'}
              style={{ color: ownerToken ? undefined : 'var(--brand-sasta, #a86a17)' }}
            >
              <Icon name="key" size={16}/>
              <span>{ownerToken ? 'STDB token' : 'Set STDB token'}</span>
            </button>
          )}
          <button className="footer__signout" onClick={signOut} title="Sign out">
            <Icon name="signout" size={16}/>
            <span>Sign out</span>
          </button>
        </div>
      </aside>

      <main className="main">
        <header className="topbar">
          <div>
            <div className="topbar__terminal">admin.sastaspace.com —</div>
            <div className="topbar__title">{PAGE_TITLES[route.path] ?? ''}</div>
          </div>
          <div className="topbar__spacer"/>
          <span className="topbar__updated">updated {secondsSince}s ago</span>
          <button className={`topbar__refresh ${refreshing ? 'spinning' : ''}`} onClick={refresh} title="Refresh">
            <Icon name="refresh" size={14}/>
          </button>
        </header>
        <div className="content" style={isLogs ? { padding: 0, overflow: 'hidden' } : {}}>
          {!isLogs && <div className="content__terminal">{`~/ admin / ${route.path === '/' ? 'dashboard' : route.path.replace(/^\//, '')}`}</div>}
          {panel}
        </div>
      </main>
      <OwnerTokenSettings open={settingsOpen} onClose={() => setSettingsOpen(false)}/>
    </div>
  );
}
