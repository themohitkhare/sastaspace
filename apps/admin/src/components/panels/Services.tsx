'use client';

import { usePoll } from '@/hooks/usePoll';
import { formatUptime, type ContainerRow } from '@/lib/data';
import Chip from '@/components/Chip';
import Icon from '@/components/Icon';

function toServiceStatus(dockerStatus: string): 'running' | 'unhealthy' | 'stopped' | 'starting' {
  if (dockerStatus === 'running') return 'running';
  if (dockerStatus === 'restarting' || dockerStatus === 'created') return 'starting';
  if (dockerStatus === 'paused' || dockerStatus === 'exited' || dockerStatus === 'dead') return 'stopped';
  return 'unhealthy';
}

function friendlyName(containerName: string): string {
  return containerName
    .replace(/^sastaspace-/, '')
    .replace(/-/g, ' ')
    .replace(/\b\w/g, c => c.toUpperCase());
}

export default function Services({ navigate }: { navigate: (path: string) => void }) {
  const { data: containers, loading, error } = usePoll<ContainerRow[]>('/containers', 15000);

  if (loading && !containers) {
    return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Loading containers…</div>;
  }
  if (error && !containers) {
    return <div className="banner banner--warn" style={{ margin: 0 }}>Failed to reach admin-api: {error}</div>;
  }
  if (!containers) return null;

  const anyDown = containers.some(c => toServiceStatus(c.status) !== 'running');
  const downCount = containers.filter(c => toServiceStatus(c.status) !== 'running').length;

  return (
    <div>
      {anyDown && (
        <div className="banner banner--warn">
          <Icon name="shield-x" size={16}/>
          <span><strong>{downCount}</strong> service{downCount === 1 ? '' : 's'} need{downCount === 1 ? 's' : ''} attention.</span>
        </div>
      )}
      <div className="grid-3">
        {containers.map(c => {
          const status = toServiceStatus(c.status);
          const uptime = status === 'running' ? formatUptime(c.uptime_s) : null;
          const memMb = c.mem_usage_mb;
          const memDisplay = memMb >= 1024 ? `${(memMb / 1024).toFixed(1)} GB` : `${memMb} MB`;
          return (
            <div key={c.name} className="service-card">
              <div className="service-card__head">
                <div className="service-card__name">{friendlyName(c.name)}</div>
                <Chip status={status}/>
              </div>
              <div className="service-card__row">
                <span>uptime</span>
                <strong>{uptime ? `up ${uptime}` : status === 'starting' ? 'starting…' : 'stopped'}</strong>
              </div>
              <div className="service-card__row">
                <span>memory</span>
                <strong>{memDisplay}</strong>
              </div>
              <div className="service-card__row">
                <span>container</span>
                <strong style={{ fontFamily: 'var(--font-mono)', fontSize: 11 }}>{c.name}</strong>
              </div>
              <div className="service-card__image">{c.image}</div>
              <div className="service-card__footer">
                <button className="btn btn--sm" onClick={() => navigate(`/logs?service=${c.name}`)}>
                  <Icon name="logs" size={12}/> Logs <Icon name="arrow-right" size={11}/>
                </button>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
