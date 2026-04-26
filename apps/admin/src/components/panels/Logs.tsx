'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTable, useReducer } from 'spacetimedb/react';
import { tables, reducers } from '@sastaspace/stdb-bindings';
import { usePoll } from '@/hooks/usePoll';
import { USE_STDB_ADMIN, useOwnerToken } from '@/hooks/useStdb';
import { adaptContainers, type ContainerStatusRow } from '@/lib/stdb-adapters';
import type { ContainerRow, LogLine } from '@/lib/data';

const ADMIN_API_URL = process.env.NEXT_PUBLIC_ADMIN_API_URL ?? 'https://api.sastaspace.com';
const MAX_LINES = 500;
const RECONNECT_MS = 600_000; // 10 min

type LogsProps = { initialService?: string; theme?: string };
type ServiceListEntry = { name: string; container: string; status: string };

function renderLogsView(opts: {
  serviceList: ServiceListEntry[];
  active: string;
  setActive: (s: string) => void;
  tail: number;
  setTail: (n: number) => void;
  filter: string;
  setFilter: (s: string) => void;
  autoScroll: boolean;
  setAutoScroll: (b: boolean) => void;
  cleared: boolean;
  setCleared: (b: boolean) => void;
  outputRef: React.RefObject<HTMLDivElement | null>;
  displayLines: LogLine[];
  theme: string;
  banner?: React.ReactNode;
}): React.ReactNode {
  const {
    serviceList, active, setActive, tail, setTail, filter, setFilter,
    autoScroll, setAutoScroll, cleared, setCleared, outputRef, displayLines, theme,
    banner,
  } = opts;

  const renderLine = (text: string): React.ReactNode => {
    if (!filter) return text;
    const re = new RegExp(`(${filter.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
    const parts = text.split(re);
    return parts.map((p, i) => re.test(p) ? <span key={i} className="log-line__hi">{p}</span> : p);
  };

  return (
    <div className="logs-layout">
      <div className="logs-sidebar">
        <div className="logs-sidebar__title">service</div>
        {serviceList.map(s => {
          const dot = s.status === 'running' ? 'var(--brand-status-live)' : s.status === 'unhealthy' ? '#b8412c' : 'var(--brand-dust)';
          return (
            <button key={s.container} className={`logs-service-item ${active === s.container ? 'active' : ''}`} onClick={() => setActive(s.container)}>
              <span className="logs-service-item__dot" style={{ background: dot }}/>
              {s.name}
            </button>
          );
        })}
      </div>
      <div className="logs-main">
        {banner}
        <div className="logs-toolbar">
          <div className="logs-toolbar__title">{serviceList.find(s => s.container === active)?.name ?? active}</div>
          <span style={{ fontFamily: 'var(--font-mono)', fontSize: 11, color: 'var(--color-fg-muted)' }}>{active}</span>
          <div className="logs-toolbar__spacer"/>
          <select className="select" value={tail} onChange={e => setTail(Number(e.target.value))}>
            <option value={50}>50 lines</option>
            <option value={200}>200 lines</option>
            <option value={500}>500 lines</option>
          </select>
          <input className="input" placeholder="Filter lines…" value={filter} onChange={e => setFilter(e.target.value)} style={{ width: 180 }}/>
          <label className="logs-toolbar__toggle">
            <input type="checkbox" checked={autoScroll} onChange={e => setAutoScroll(e.target.checked)}/>
            Auto-scroll
          </label>
          <button className="btn btn--sm btn--ghost" onClick={() => setCleared(true)}>Clear</button>
        </div>
        <div ref={outputRef} className={`logs-output ${theme === 'light' ? 'logs-output--light' : ''}`}>
          {displayLines.length === 0 && (
            <div style={{ color: theme === 'light' ? 'var(--color-fg-muted)' : '#6b6760', fontStyle: 'italic' }}>
              {cleared ? '(cleared — new lines will appear here)' : filter ? `No lines matching "${filter}"` : 'Waiting for log lines…'}
            </div>
          )}
          {displayLines.map((l, i) => (
            <div key={i} className={`log-line ${l.level ? `log-line--${l.level}` : ''}`}>
              <span className="log-line__ts">{l.ts}</span>
              <span>{renderLine(l.text)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function LogsLegacy({ initialService, theme = 'dark' }: LogsProps) {
  const { data: containers } = usePoll<ContainerRow[]>('/containers', 30000);
  const [active, setActive] = useState(initialService ?? 'sastaspace-stdb');
  const [tail, setTail] = useState(200);
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [lines, setLines] = useState<LogLine[]>([]);
  const [cleared, setCleared] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    esRef.current?.close();
    setLines([]);
    setCleared(false);

    const url = `${ADMIN_API_URL}/logs/${encodeURIComponent(active)}?tail=${tail}`;
    const es = new EventSource(url);
    esRef.current = es;

    const reconnectId = setTimeout(() => { es.close(); }, RECONNECT_MS);

    es.onmessage = (e) => {
      try {
        const line = JSON.parse(e.data) as LogLine;
        setLines(prev => {
          const next = [...prev, line];
          return next.length > MAX_LINES ? next.slice(-MAX_LINES) : next;
        });
      } catch { /* ignore malformed */ }
    };

    return () => {
      clearTimeout(reconnectId);
      es.close();
    };
  }, [active, tail]);

  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [lines.length, autoScroll]);

  const displayLines = cleared
    ? []
    : filter
    ? lines.filter(l => l.text.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  const serviceList: ServiceListEntry[] = containers
    ? containers.map(c => ({
        name: c.name.replace(/^sastaspace-/, '').replace(/-/g, ' ').replace(/\b\w/g, x => x.toUpperCase()),
        container: c.name,
        status: c.status,
      }))
    : [{ name: active, container: active, status: 'unknown' }];

  return renderLogsView({
    serviceList, active, setActive, tail, setTail, filter, setFilter,
    autoScroll, setAutoScroll, cleared, setCleared, outputRef, displayLines, theme,
  });
}

function LogsStdb({ initialService, theme = 'dark' }: LogsProps) {
  const ownerToken = useOwnerToken();
  const [statusRows] = useTable(tables.container_status);
  const [active, setActive] = useState(initialService ?? 'sastaspace-stdb');
  const [tail, setTail] = useState(200);
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [cleared, setCleared] = useState(false);
  const outputRef = useRef<HTMLDivElement>(null);

  // Reset cleared flag when the active container changes (so a switch always
  // shows fresh lines instead of staying blank).
  useEffect(() => {
    setCleared(false);
  }, [active]);

  // log_event subscription filtered server-side by container.
  const logQuery = useMemo(() => tables.log_event.where(r => r.container.eq(active)), [active]);
  const [logRows] = useTable(logQuery);

  // Reducer hooks for log_interest. Owner-only — silently no-op without a token.
  const addInterest = useReducer(reducers.addLogInterest);
  const removeInterest = useReducer(reducers.removeLogInterest);

  // Manage log_interest lifecycle: on mount + on container switch, add the
  // current container; on unmount + before next switch, remove the previous.
  useEffect(() => {
    if (!ownerToken) return;
    const container = active;
    addInterest({ container }).catch(() => { /* silent — no perms or worker absent */ });
    return () => {
      removeInterest({ container }).catch(() => { /* same */ });
    };
    // addInterest/removeInterest are stable refs from useReducer
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, ownerToken]);

  // Auto-scroll on new lines
  const lines: LogLine[] = useMemo(() => {
    return [...logRows]
      .sort((a, b) => Number(a.tsMicros - b.tsMicros))
      .slice(-tail)
      .map(r => {
        const ms = Number(r.tsMicros / 1000n);
        const ts = new Date(ms);
        const hh = ts.getHours().toString().padStart(2, '0');
        const mm = ts.getMinutes().toString().padStart(2, '0');
        const ss = ts.getSeconds().toString().padStart(2, '0');
        const msStr = ts.getMilliseconds().toString().padStart(3, '0');
        return { ts: `${hh}:${mm}:${ss}.${msStr}`, text: r.text, level: r.level };
      });
  }, [logRows, tail]);

  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [lines.length, autoScroll]);

  const displayLines = cleared
    ? []
    : filter
    ? lines.filter(l => l.text.toLowerCase().includes(filter.toLowerCase()))
    : lines;

  // Service list from container_status (or fallback to active alone).
  const containers = adaptContainers(statusRows as readonly ContainerStatusRow[]);
  const serviceList: ServiceListEntry[] = containers.length
    ? containers.map(c => ({
        name: c.name.replace(/^sastaspace-/, '').replace(/-/g, ' ').replace(/\b\w/g, x => x.toUpperCase()),
        container: c.name,
        status: c.status,
      }))
    : [{ name: active, container: active, status: 'unknown' }];

  // Read-only banner if no owner token: log_interest can't be registered, so
  // we only see whatever the worker is already streaming for someone else.
  const banner = !ownerToken ? (
    <div className="banner banner--warn" style={{ margin: '10px 18px 0' }}>
      Read-only mode — paste your STDB owner token in the sidebar to register log interest for this container.
    </div>
  ) : undefined;

  return renderLogsView({
    serviceList, active, setActive, tail, setTail, filter, setFilter,
    autoScroll, setAutoScroll, cleared, setCleared, outputRef, displayLines, theme,
    banner,
  });
}

export default function Logs(props: LogsProps) {
  if (USE_STDB_ADMIN) return <LogsStdb {...props}/>;
  return <LogsLegacy {...props}/>;
}
