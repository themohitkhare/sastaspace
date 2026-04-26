'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useTable, useReducer } from 'spacetimedb/react';
import { tables, reducers } from '@sastaspace/stdb-bindings';
import { usePoll } from '@/hooks/usePoll';
import { USE_STDB_ADMIN, useOwnerToken } from '@/hooks/useStdb';
import { adaptContainers, type ContainerStatusRow } from '@/lib/stdb-adapters';
import type { ContainerRow, LogLine } from '@/lib/types';

// Phase 3: default-empty after N6. The Logs legacy path skips the EventSource
// when this is empty so the panel doesn't probe a dead host.
const ADMIN_API_URL = process.env.NEXT_PUBLIC_ADMIN_API_URL ?? '';
const MAX_LINES = 500;
const RECONNECT_MS = 600_000; // 10 min

type LogsProps = { initialService?: string; theme?: string };
type ServiceListEntry = { name: string; container: string; status: string };

type LogsViewProps = {
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
  displayLines: LogLine[];
  theme: string;
  banner?: React.ReactNode;
};

function LogsView({
  serviceList, active, setActive, tail, setTail, filter, setFilter,
  autoScroll, setAutoScroll, cleared, setCleared, displayLines, theme, banner,
}: LogsViewProps) {
  const outputRef = useRef<HTMLDivElement>(null);

  // Auto-scroll on new lines.
  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [displayLines.length, autoScroll]);

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
  // Keyed by `${active}:${tail}` so a switch re-mounts the buffer instead of
  // requiring a setState-in-effect reset.
  const epoch = `${active}:${tail}`;
  const [linesByEpoch, setLinesByEpoch] = useState<{ epoch: string; lines: LogLine[]; cleared: boolean }>({ epoch, lines: [], cleared: false });

  // Establish/reset the EventSource on epoch change and route incoming lines
  // into the matching epoch's buffer (drop stragglers from old epochs).
  useEffect(() => {
    // After Phase 3 N6, legacy ADMIN_API_URL defaults to '' so a misconfigured
    // build doesn't probe a dead host. Bail cleanly — STDB path replaces this.
    if (!ADMIN_API_URL) return;
    const url = `${ADMIN_API_URL}/logs/${encodeURIComponent(active)}?tail=${tail}`;
    const es = new EventSource(url);
    const reconnectId = setTimeout(() => { es.close(); }, RECONNECT_MS);
    // Buffer reset on epoch change is the whole point of this effect.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLinesByEpoch({ epoch, lines: [], cleared: false });
    es.onmessage = (e) => {
      try {
        const line = JSON.parse(e.data) as LogLine;
        setLinesByEpoch(prev => prev.epoch !== epoch ? prev : {
          epoch,
          cleared: prev.cleared,
          lines: prev.lines.length >= MAX_LINES
            ? [...prev.lines.slice(-(MAX_LINES - 1)), line]
            : [...prev.lines, line],
        });
      } catch { /* ignore malformed */ }
    };
    return () => { clearTimeout(reconnectId); es.close(); };
  }, [epoch, active, tail]);

  const setCleared = (cleared: boolean) => setLinesByEpoch(prev => ({ ...prev, cleared }));
  const { lines, cleared } = linesByEpoch;
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

  return (
    <LogsView
      serviceList={serviceList} active={active} setActive={setActive}
      tail={tail} setTail={setTail} filter={filter} setFilter={setFilter}
      autoScroll={autoScroll} setAutoScroll={setAutoScroll}
      cleared={cleared} setCleared={setCleared}
      displayLines={displayLines} theme={theme}
    />
  );
}

function LogsStdb({ initialService, theme = 'dark' }: LogsProps) {
  const ownerToken = useOwnerToken();
  const [statusRows] = useTable(tables.container_status);
  const [active, setActive] = useState(initialService ?? 'sastaspace-stdb');
  const [tail, setTail] = useState(200);
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  // `cleared` is keyed by active container so a container switch resets
  // it without needing a setState-in-effect.
  const [clearedFor, setClearedFor] = useState<string | null>(null);
  const cleared = clearedFor === active;
  const setCleared = (b: boolean) => setClearedFor(b ? active : null);

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

  return (
    <LogsView
      serviceList={serviceList} active={active} setActive={setActive}
      tail={tail} setTail={setTail} filter={filter} setFilter={setFilter}
      autoScroll={autoScroll} setAutoScroll={setAutoScroll}
      cleared={cleared} setCleared={setCleared}
      displayLines={displayLines} theme={theme} banner={banner}
    />
  );
}

export default function Logs(props: LogsProps) {
  if (USE_STDB_ADMIN) return <LogsStdb {...props}/>;
  return <LogsLegacy {...props}/>;
}
