'use client';

import { useEffect, useRef, useState } from 'react';
import { usePoll } from '@/hooks/usePoll';
import type { SystemMetrics } from '@/lib/data';
import LineChart from '@/components/charts/LineChart';
import AreaChart from '@/components/charts/AreaChart';

const HISTORY_LEN = 60;

export default function Server() {
  const { data, loading, error } = usePoll<SystemMetrics>('/system', 3000);

  const cpuHistory = useRef<number[]>([]);
  const memHistory = useRef<number[]>([]);
  const netTxHistory = useRef<number[]>([]);
  const netRxHistory = useRef<number[]>([]);
  const prevNet = useRef<{ tx: number; rx: number } | null>(null);
  const [, forceRender] = useState(0);

  useEffect(() => {
    if (!data) return;
    const push = (arr: number[], val: number) => {
      arr.push(val);
      if (arr.length > HISTORY_LEN) arr.shift();
    };
    push(cpuHistory.current, data.cpu.pct);
    push(memHistory.current, data.mem.used_gb);

    const prev = prevNet.current;
    if (prev) {
      push(netTxHistory.current, Math.max(0, (data.net.tx_bytes - prev.tx) / 1e6));
      push(netRxHistory.current, Math.max(0, (data.net.rx_bytes - prev.rx) / 1e6));
    }
    prevNet.current = { tx: data.net.tx_bytes, rx: data.net.rx_bytes };
    forceRender(n => n + 1);
  }, [data]);

  if (loading && !data) {
    return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Connecting to admin-api…</div>;
  }
  if (error && !data) {
    return <div className="banner banner--warn" style={{ margin: 0 }}>Failed to reach admin-api: {error}</div>;
  }
  if (!data) return null;

  const colorVar = (c: string) => c === 'green' ? '#4a7c3f' : c === 'yellow' ? '#a86a17' : '#b8412c';
  const cpuColor = data.cpu.pct < 50 ? 'green' : data.cpu.pct < 80 ? 'yellow' : 'red';
  const memPct = (data.mem.used_gb / data.mem.total_gb) * 100;
  const memColor = memPct < 70 ? 'green' : memPct < 85 ? 'yellow' : 'red';
  const diskColor = data.disk.pct < 80 ? 'green' : data.disk.pct < 90 ? 'yellow' : 'red';

  return (
    <div>
      <div className="grid-4">
        <div className="card">
          <div className="card__head"><span className="card__label">cpu</span><span className="card__sub">{data.cpu.cores} cores</span></div>
          <div className={`card__value card__value--${cpuColor}`}>{data.cpu.pct}%</div>
          <div className="bar"><div className="bar__fill" style={{ width: `${data.cpu.pct}%`, background: colorVar(cpuColor) }}/></div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">memory</span></div>
          <div className={`card__value card__value--${memColor}`}>{data.mem.used_gb.toFixed(1)} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {data.mem.total_gb.toFixed(0)} GB</span></div>
          <div className="bar"><div className="bar__fill" style={{ width: `${memPct}%`, background: colorVar(memColor) }}/></div>
          <div className="card__sub">swap {data.mem.swap_used_mb} / {data.mem.swap_total_mb} MB</div>
        </div>
        <div className="card">
          <div className="card__head"><span className="card__label">disk</span></div>
          <div className={`card__value card__value--${diskColor}`}>{data.disk.used_gb} <span style={{ fontSize: 18, color: 'var(--color-fg-muted)' }}>/ {data.disk.total_gb} GB</span></div>
          <div className="bar"><div className="bar__fill" style={{ width: `${data.disk.pct}%`, background: colorVar(diskColor) }}/></div>
          <div className="card__sub">{data.disk.mount}</div>
        </div>
        {data.gpu ? (
          <div className="card">
            <div className="card__head"><span className="card__label">gpu</span><span className="card__sub">{data.gpu.temp_c}°C</span></div>
            <div className="card__value">{data.gpu.pct}%</div>
            <div className="card__sub">vram {data.gpu.vram_used_mb} / {data.gpu.vram_total_mb} MB</div>
            <div className="card__sub" style={{ marginTop: 4 }}>{data.gpu.model}</div>
          </div>
        ) : (
          <div className="card">
            <div className="card__head"><span className="card__label">gpu</span></div>
            <div className="card__value card__value--green" style={{ fontSize: 14 }}>n/a</div>
            <div className="card__sub">no GPU detected</div>
          </div>
        )}
      </div>

      <div style={{ height: 28 }}/>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">CPU %</div>
          <div className="chart-card__sub">live · 3s resolution · last {cpuHistory.current.length} samples</div>
        </div>
        <LineChart data={cpuHistory.current.length ? cpuHistory.current : [0]} color="var(--brand-ink)" yMax={100} yLabel="%" fill/>
      </div>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">Memory (GB)</div>
          <div className="chart-card__sub">live · ceiling {data.mem.total_gb.toFixed(0)} GB</div>
        </div>
        <LineChart data={memHistory.current.length ? memHistory.current : [0]} color="var(--brand-rust)" yMax={data.mem.total_gb} fill/>
      </div>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">Network I/O (MB/s)</div>
          <div className="chart-card__sub" style={{ display: 'flex', gap: 14 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 2, background: 'var(--brand-ink)', display: 'inline-block' }}/>tx
            </span>
            <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6 }}>
              <span style={{ width: 10, height: 2, background: 'var(--brand-sasta)', display: 'inline-block' }}/>rx
            </span>
          </div>
        </div>
        <AreaChart tx={netTxHistory.current.length ? netTxHistory.current : [0]} rx={netRxHistory.current.length ? netRxHistory.current : [0]}/>
      </div>
    </div>
  );
}
