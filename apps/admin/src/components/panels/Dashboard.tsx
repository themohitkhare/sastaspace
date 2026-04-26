'use client';

import { COMMENTS, SERVICES, SYSTEM, CPU_HISTORY, relTime } from '@/lib/data';
import Chip from '@/components/Chip';
import Sparkline from '@/components/charts/Sparkline';
import Icon from '@/components/Icon';

export default function Dashboard({ navigate }: { navigate: (path: string) => void }) {
  const pendingCount = COMMENTS.filter(c => c.status === 'pending' || c.status === 'flagged').length;
  const lastHour = COMMENTS.filter(c => (Date.now() - new Date(c.createdAt).getTime()) < 3600000).length;
  const healthy = SERVICES.filter(s => s.status === 'running').length;
  const recentComments = [...COMMENTS].sort((a, b) => new Date(b.createdAt).getTime() - new Date(a.createdAt).getTime()).slice(0, 5);

  const cpuColor = SYSTEM.cpu.pct < 50 ? 'green' : SYSTEM.cpu.pct < 80 ? 'yellow' : 'red';
  const memPct = (SYSTEM.mem.used / SYSTEM.mem.total) * 100;
  const memColor = memPct < 70 ? 'green' : memPct < 85 ? 'yellow' : 'red';

  return (
    <div>
      <div className="grid-4">
        <div className="card card--clickable" onClick={() => navigate('/comments?status=pending')}>
          <div className="card__head"><span className="card__label">pending comments</span></div>
          <div className={`card__value ${pendingCount > 0 ? 'card__value--yellow' : 'card__value--green'}`}>{pendingCount}</div>
          <div className="card__sub">{lastHour} submitted in the last hour</div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">cpu</span><span className="card__sub">{SYSTEM.cpu.cores} cores</span></div>
          <div className={`card__value card__value--${cpuColor}`}>{SYSTEM.cpu.pct}%</div>
          <Sparkline data={CPU_HISTORY.slice(-10)} color={cpuColor === 'green' ? 'var(--brand-status-live)' : cpuColor === 'yellow' ? 'var(--brand-sasta)' : 'var(--brand-rust)'} fill/>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">memory</span><span className="card__sub">swap {SYSTEM.mem.swapUsed} / {SYSTEM.mem.swapTotal} MB</span></div>
          <div className={`card__value card__value--${memColor}`}>{SYSTEM.mem.used} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {SYSTEM.mem.total} GB</span></div>
          <div className="bar"><div className={`bar__fill bar__fill--${memColor}`} style={{ width: `${memPct}%` }}/></div>
        </div>
        <div className="card card--clickable" onClick={() => navigate('/services')}>
          <div className="card__head"><span className="card__label">services</span></div>
          <div className={`card__value ${healthy === SERVICES.length ? 'card__value--green' : 'card__value--red'}`}>
            {healthy} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {SERVICES.length} healthy</span>
          </div>
          <div className="card__sub">{SERVICES.length - healthy > 0 ? `${SERVICES.length - healthy} need attention` : 'all containers up'}</div>
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
            {SERVICES.map(s => {
              const dotColor = s.status === 'running' ? 'var(--brand-status-live)' : s.status === 'unhealthy' ? '#b8412c' : 'var(--brand-dust)';
              return (
                <div key={s.container} className="service-row" onClick={() => navigate('/services')}>
                  <span className="service-row__dot" style={{ background: dotColor }}/>
                  <span className="service-row__name">{s.name}</span>
                  <span className="service-row__uptime">{s.status === 'running' ? `up ${s.uptime}` : s.status}</span>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
}
