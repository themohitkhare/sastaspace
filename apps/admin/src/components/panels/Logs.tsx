'use client';

import { useState, useEffect, useRef } from 'react';
import { SERVICES, LOG_TEMPLATES } from '@/lib/data';

type LogsProps = { initialService?: string; theme?: string };

export default function Logs({ initialService, theme = 'dark' }: LogsProps) {
  const [active, setActive] = useState(initialService ?? 'sastaspace-stdb');
  const [tail, setTail] = useState(200);
  const [filter, setFilter] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [clearedMap, setClearedMap] = useState<Record<string, boolean>>({});
  const cleared = clearedMap[active] ?? false;
  const outputRef = useRef<HTMLDivElement>(null);

  let lines = LOG_TEMPLATES[active] ?? [];
  if (cleared) lines = [];
  let displayLines = filter
    ? lines.filter(l => l.text.toLowerCase().includes(filter.toLowerCase()))
    : lines;
  displayLines = displayLines.slice(0, tail);

  useEffect(() => {
    if (autoScroll && outputRef.current) {
      outputRef.current.scrollTop = outputRef.current.scrollHeight;
    }
  }, [active, displayLines.length, autoScroll]);

  const lineKind = (text: string): string | null => {
    if (/\bERROR\b/.test(text)) return 'error';
    if (/\bWARN\b/.test(text)) return 'warn';
    if (/\bDEBUG\b/.test(text)) return 'debug';
    return null;
  };

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
        {SERVICES.map(s => {
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
        <div className="logs-toolbar">
          <div className="logs-toolbar__title">{SERVICES.find(s => s.container === active)?.name}</div>
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
          <button className="btn btn--sm btn--ghost" onClick={() => setClearedMap(prev => ({ ...prev, [active]: true }))}>Clear</button>
        </div>
        <div ref={outputRef} className={`logs-output ${theme === 'light' ? 'logs-output--light' : ''}`}>
          {displayLines.length === 0 && (
            <div style={{ color: theme === 'light' ? 'var(--color-fg-muted)' : '#6b6760', fontStyle: 'italic' }}>
              {cleared ? '(cleared — new lines will appear here)' : filter ? `No lines matching "${filter}"` : 'No log lines.'}
            </div>
          )}
          {displayLines.map((l, i) => {
            const kind = lineKind(l.text);
            return (
              <div key={i} className={`log-line ${kind ? `log-line--${kind}` : ''}`}>
                <span className="log-line__ts">{l.ts}</span>
                <span>{renderLine(l.text)}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
