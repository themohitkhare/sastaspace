'use client';

import { SYSTEM, CPU_HISTORY, MEM_HISTORY_GB, NET_TX, NET_RX } from '@/lib/data';
import LineChart from '@/components/charts/LineChart';
import AreaChart from '@/components/charts/AreaChart';

export default function Server() {
  const cpuColor = SYSTEM.cpu.pct < 50 ? 'green' : SYSTEM.cpu.pct < 80 ? 'yellow' : 'red';
  const memPct = (SYSTEM.mem.used / SYSTEM.mem.total) * 100;
  const memColor = memPct < 70 ? 'green' : memPct < 85 ? 'yellow' : 'red';
  const diskColor = SYSTEM.disk.pct < 80 ? 'green' : SYSTEM.disk.pct < 90 ? 'yellow' : 'red';
  const colorVar = (c: string) => c === 'green' ? '#4a7c3f' : c === 'yellow' ? '#a86a17' : '#b8412c';

  return (
    <div>
      <div className="grid-4">
        <div className="card">
          <div className="card__head"><span className="card__label">cpu</span><span className="card__sub">{SYSTEM.cpu.cores} cores</span></div>
          <div className={`card__value card__value--${cpuColor}`}>{SYSTEM.cpu.pct}%</div>
          <div className="bar"><div className="bar__fill" style={{ width: `${SYSTEM.cpu.pct}%`, background: colorVar(cpuColor) }}/></div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">memory</span></div>
          <div className={`card__value card__value--${memColor}`}>{SYSTEM.mem.used} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {SYSTEM.mem.total} GB</span></div>
          <div className="bar"><div className="bar__fill" style={{ width: `${memPct}%`, background: colorVar(memColor) }}/></div>
          <div className="card__sub">swap {SYSTEM.mem.swapUsed} / {SYSTEM.mem.swapTotal} MB</div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">disk</span></div>
          <div className={`card__value card__value--${diskColor}`}>{SYSTEM.disk.used} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {SYSTEM.disk.total} GB</span></div>
          <div className="bar"><div className="bar__fill" style={{ width: `${SYSTEM.disk.pct}%`, background: colorVar(diskColor) }}/></div>
          <div className="card__sub">{SYSTEM.disk.mount}</div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">gpu</span><span className="card__sub">{SYSTEM.gpu.temp}°C</span></div>
          <div className="card__value">{SYSTEM.gpu.pct}%</div>
          <div className="card__sub">vram {SYSTEM.gpu.vramUsed} / {SYSTEM.gpu.vramTotal} MB</div>
          <div className="card__sub" style={{ marginTop: 4 }}>{SYSTEM.gpu.model}</div>
        </div>
      </div>

      <div style={{ height: 28 }}/>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">CPU %</div>
          <div className="chart-card__sub">last 60 minutes · 1-min resolution</div>
        </div>
        <LineChart data={CPU_HISTORY} color="var(--brand-ink)" yMax={100} yLabel="%" fill/>
      </div>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">Memory (GB)</div>
          <div className="chart-card__sub">last 60 minutes · ceiling {SYSTEM.mem.total} GB</div>
        </div>
        <LineChart data={MEM_HISTORY_GB} color="var(--brand-rust)" yMax={SYSTEM.mem.total} fill/>
      </div>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">Network I/O</div>
          <div className="chart-card__sub" style={{ display: 'flex', gap: 14 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 2, background: 'var(--brand-ink)', display: 'inline-block' }}/>tx
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 2, background: 'var(--brand-sasta)', display: 'inline-block' }}/>rx
            </span>
          </div>
        </div>
        <AreaChart tx={NET_TX} rx={NET_RX}/>
      </div>
    </div>
  );
}
