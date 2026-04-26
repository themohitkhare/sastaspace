'use client';

import { useMemo } from 'react';
import { useSpacetimeDB, useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/stdb-bindings';
import { usePoll } from '@/hooks/usePoll';
import { relTime, formatUptime, type SystemMetrics, type ContainerRow } from '@/lib/data';
import Chip from '@/components/Chip';
import Sparkline from '@/components/charts/Sparkline';
import Icon from '@/components/Icon';

function DashboardInner({ navigate }: { navigate: (path: string) => void }) {
  const { isActive } = useSpacetimeDB();
  const [commentRows] = useTable(tables.comment);
  const { data: containers } = usePoll<ContainerRow[]>('/containers', 15000);
  const { data: system } = usePoll<SystemMetrics>('/system', 3000);

  const pendingCount = useMemo(
    () => commentRows.filter(c => c.status === 'pending' || c.status === 'flagged').length,
    [commentRows],
  );
  const lastHourCount = useMemo(() => {
    const cutoff = Date.now() - 3_600_000;
    return commentRows.filter(c => {
      const ms = c.createdAt instanceof Date ? c.createdAt.getTime()
        : typeof c.createdAt === 'bigint' ? Number(c.createdAt / 1000n)
        : new Date(String(c.createdAt)).getTime();
      return ms >= cutoff;
    }).length;
  }, [commentRows]);

  const recentComments = useMemo(() => {
    return [...commentRows]
      .sort((a, b) => {
        const toMs = (v: unknown) => v instanceof Date ? v.getTime()
          : typeof v === 'bigint' ? Number(v / 1000n)
          : new Date(String(v)).getTime();
        return toMs(b.createdAt) - toMs(a.createdAt);
      })
      .slice(0, 5)
      .map(c => ({
        id: String(c.id),
        status: c.status as 'pending' | 'flagged' | 'approved' | 'rejected',
        author: c.authorName || 'anonymous',
        post: c.postSlug,
        body: c.body,
        createdAt: c.createdAt instanceof Date ? c.createdAt.toISOString()
          : typeof c.createdAt === 'bigint' ? new Date(Number(c.createdAt / 1000n)).toISOString()
          : String(c.createdAt),
      }));
  }, [commentRows]);

  const healthy = containers ? containers.filter(c => c.status === 'running').length : 0;
  const total = containers?.length ?? 0;
  const cpuPct = system?.cpu.pct ?? 0;
  const cpuColor = cpuPct < 50 ? 'green' : cpuPct < 80 ? 'yellow' : 'red';
  const memPct = system ? (system.mem.used_gb / system.mem.total_gb) * 100 : 0;
  const memColor = memPct < 70 ? 'green' : memPct < 85 ? 'yellow' : 'red';

  return (
    <div>
      <div className="grid-4">
        <div className="card card--clickable" onClick={() => navigate('/comments?status=pending')}>
          <div className="card__head"><span className="card__label">pending comments</span></div>
          <div className={`card__value ${!isActive ? 'card__value--green' : pendingCount > 0 ? 'card__value--yellow' : 'card__value--green'}`}>
            {isActive ? pendingCount : '…'}
          </div>
          <div className="card__sub">{isActive ? `${lastHourCount} submitted in the last hour` : 'connecting…'}</div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">cpu</span>{system && <span className="card__sub">{system.cpu.cores} cores</span>}</div>
          <div className={`card__value card__value--${cpuColor}`}>{system ? `${cpuPct}%` : '…'}</div>
          {system && <Sparkline data={[cpuPct]} color={cpuColor === 'green' ? 'var(--brand-status-live)' : cpuColor === 'yellow' ? 'var(--brand-sasta)' : 'var(--brand-rust)'} fill/>}
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">memory</span>{system && <span className="card__sub">swap {system.mem.swap_used_mb} / {system.mem.swap_total_mb} MB</span>}</div>
          <div className={`card__value card__value--${memColor}`}>
            {system ? <>{system.mem.used_gb.toFixed(1)} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {system.mem.total_gb.toFixed(0)} GB</span></> : '…'}
          </div>
          {system && <div className="bar"><div className={`bar__fill bar__fill--${memColor}`} style={{ width: `${memPct}%` }}/></div>}
        </div>
        <div className="card card--clickable" onClick={() => navigate('/services')}>
          <div className="card__head"><span className="card__label">services</span></div>
          <div className={`card__value ${!containers ? '' : healthy === total ? 'card__value--green' : 'card__value--red'}`}>
            {containers ? <>{healthy} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {total} healthy</span></> : '…'}
          </div>
          <div className="card__sub">{containers ? (total - healthy > 0 ? `${total - healthy} need attention` : 'all containers up') : 'loading…'}</div>
        </div>
      </div>

      <div style={{ height: 28 }}/>

      <div className="split-2">
        <div>
          <div className="section__head">
            <h2 className="section__title">Recent comments</h2>
            <button className="btn btn--ghost btn--sm" onClick={() => navigate('/comments')}>View all <Icon name="arrow-right" size={12}/></button>
          </div>
          <div className="card" style={{ padding: '4px 22px' }}>
            {!isActive && <div style={{ padding: '20px 0', color: 'var(--color-fg-muted)', fontSize: 13 }}>Connecting…</div>}
            {isActive && recentComments.length === 0 && <div style={{ padding: '20px 0', color: 'var(--color-fg-muted)', fontSize: 13 }}>No comments yet.</div>}
            {recentComments.map(c => (
              <div key={c.id} className="recent-row">
                <Chip status={c.status}/>
                <div className="recent-row__main">
                  <div className="recent-row__top">
                    <span className="recent-row__author">{c.author}</span>
                    <span className="muted">·</span>
                    <span className="recent-row__post">{c.post}</span>
                  </div>
                  <div className="recent-row__body">{c.body}</div>
                </div>
                <span className="recent-row__time">{relTime(c.createdAt)}</span>
              </div>
            ))}
          </div>
        </div>

        <div>
          <div className="section__head">
            <h2 className="section__title">Services</h2>
            <button className="btn btn--ghost btn--sm" onClick={() => navigate('/services')}>View all <Icon name="arrow-right" size={12}/></button>
          </div>
          <div className="card" style={{ padding: '4px 22px' }}>
            {!containers && <div style={{ padding: '20px 0', color: 'var(--color-fg-muted)', fontSize: 13 }}>Loading…</div>}
            {containers?.map(c => {
              const dotColor = c.status === 'running' ? 'var(--brand-status-live)' : c.status === 'unhealthy' ? '#b8412c' : 'var(--brand-dust)';
              const name = c.name.replace(/^sastaspace-/, '').replace(/-/g, ' ').replace(/\b\w/g, x => x.toUpperCase());
              return (
                <div key={c.name} className="service-row" onClick={() => navigate('/services')}>
                  <span className="service-row__dot" style={{ background: dotColor }}/>
                  <span className="service-row__name">{name}</span>
                  <span className="service-row__uptime">{c.status === 'running' ? `up ${formatUptime(c.uptime_s)}` : c.status}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Dashboard({ navigate }: { navigate: (path: string) => void }) {
  return <DashboardInner navigate={navigate}/>;
}
