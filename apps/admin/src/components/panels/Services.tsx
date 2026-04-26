'use client';

import { useState } from 'react';
import { SERVICES, Service } from '@/lib/data';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';

export default function Services({ navigate }: { navigate: (path: string) => void }) {
  const [confirmRestart, setConfirmRestart] = useState<Service | null>(null);
  const [restarting, setRestarting] = useState<string | null>(null);
  const [services, setServices] = useState<Service[]>(SERVICES);
  const anyDown = services.some(s => s.status !== 'running');

  const doRestart = () => {
    const target = confirmRestart;
    if (!target) return;
    setConfirmRestart(null);
    setRestarting(target.container);
    setServices(prev => prev.map(s => s.container === target.container ? { ...s, status: 'starting' as const } : s));
    setTimeout(() => {
      setServices(prev => prev.map(s => s.container === target.container ? { ...s, status: 'running' as const, uptime: '0m', uptimeMin: 0 } : s));
      setRestarting(null);
    }, 1800);
  };

  const downCount = services.filter(s => s.status !== 'running').length;

  return (
    <div>
      {anyDown && (
        <div className="banner banner--warn">
          <Icon name="shield-x" size={16}/>
          <span><strong>{downCount}</strong> service{downCount === 1 ? '' : 's'} need{downCount === 1 ? 's' : ''} attention. Restart or check logs.</span>
        </div>
      )}
      <div className="grid-3">
        {services.map(s => (
          <div key={s.container} className="service-card">
            <div className="service-card__head">
              <div className="service-card__name">{s.name}</div>
              <Chip status={s.status}/>
            </div>
            <div className="service-card__row">
              <span>uptime</span>
              <strong>{s.status === 'running' ? `up ${s.uptime}` : s.status === 'starting' ? 'starting…' : 'stopped'}</strong>
            </div>
            <div className="service-card__row">
              <span>memory</span>
              <strong>{s.mem}</strong>
            </div>
            <div className="service-card__row">
              <span>container</span>
              <strong style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{s.container}</strong>
            </div>
            <div className="service-card__image">{s.image}</div>
            <div className="service-card__footer">
              <button className="btn btn--sm" onClick={() => navigate(`/logs?service=${s.container}`)}>
                <Icon name="logs" size={12}/> Logs <Icon name="arrow-right" size={11}/>
              </button>
              <span style={{ flex: 1 }}/>
              <button className="btn btn--sm btn--danger" disabled={restarting === s.container} onClick={() => setConfirmRestart(s)}>
                <Icon name="restart" size={12}/> {restarting === s.container ? 'Restarting…' : 'Restart'}
              </button>
            </div>
          </div>
        ))}
      </div>

      {confirmRestart && (
        <div className="modal-overlay" onClick={() => setConfirmRestart(null)}>
          <div className="modal" onClick={e => e.stopPropagation()}>
            <div className="modal__title">Restart {confirmRestart.name}?</div>
            <div className="modal__body">The service will be briefly unavailable.</div>
            <div className="modal__actions">
              <button className="btn btn--ghost" onClick={() => setConfirmRestart(null)}>Cancel</button>
              <button className="btn btn--danger-solid" onClick={doRestart}><Icon name="restart" size={13}/> Restart</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
