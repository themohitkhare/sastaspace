'use client';

import { useState, useEffect } from 'react';
import Icon from '@/components/Icon';
import Dashboard from '@/components/panels/Dashboard';
import Comments from '@/components/panels/Comments';
import Server from '@/components/panels/Server';
import Services from '@/components/panels/Services';
import TypeWars from '@/components/panels/TypeWars';
import Logs from '@/components/panels/Logs';
import AuthSignIn from '@/components/auth/AuthSignIn';
import AuthDenied from '@/components/auth/AuthDenied';
import { COMMENTS, SERVICES } from '@/lib/data';

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

export default function Shell() {
  const [route, setRoute] = useState<Route>({ path: '/', params: new URLSearchParams() });
  const [authState, setAuthState] = useState<AuthState>('loading');
  const [userEmail, setUserEmail] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [updatedAt, setUpdatedAt] = useState(Date.now());
  const [refreshing, setRefreshing] = useState(false);
  const [tick, setTick] = useState(0);

  // Resolve auth on mount
  useEffect(() => {
    const token = readToken();
    if (!token) {
      setAuthState('signin');
      return;
    }
    setUserEmail(token.email);
    if (OWNER_EMAIL && token.email !== OWNER_EMAIL) {
      setAuthState('denied');
    } else {
      setAuthState('app');
    }
  }, []);

  // Hash routing
  useEffect(() => {
    setRoute(parsePath());
    const onHash = () => setRoute(parsePath());
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  // Tick for "updated X seconds ago"
  useEffect(() => {
    const id = setInterval(() => setTick(t => t + 1), 1000);
    return () => clearInterval(id);
  }, [tick]);

  const navigate = (p: string) => { window.location.hash = p; };

  const refresh = () => {
    setRefreshing(true);
    setTimeout(() => { setRefreshing(false); setUpdatedAt(Date.now()); }, 600);
  };

  const signOut = () => {
    localStorage.removeItem('admin_token');
    setAuthState('signin');
  };

  if (authState === 'loading') {
    return <div className="auth-shell"><div className="spinner"/></div>;
  }

  if (authState === 'signin') {
    return <AuthSignIn onSuccess={() => {
      const token = readToken();
      if (!token) return;
      setUserEmail(token.email);
      if (OWNER_EMAIL && token.email !== OWNER_EMAIL) {
        setAuthState('denied');
      } else {
        setAuthState('app');
      }
    }}/>;
  }

  if (authState === 'denied') {
    return <AuthDenied email={userEmail} onSignOut={signOut}/>;
  }

  const pendingCount = COMMENTS.filter(c => c.status === 'pending' || c.status === 'flagged').length;
  const anyDown = SERVICES.some(s => s.status !== 'running');
  const secondsSince = Math.floor((Date.now() - updatedAt) / 1000);
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
    </div>
  );
}
