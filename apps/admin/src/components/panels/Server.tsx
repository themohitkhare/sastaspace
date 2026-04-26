'use client';

import { useEffect, useRef, useState } from 'react';
import { useTable } from 'spacetimedb/react';
import { tables } from '@sastaspace/stdb-bindings';
import { usePoll } from '@/hooks/usePoll';
import { USE_STDB_ADMIN } from '@/hooks/useStdb';
import type { SystemMetrics } from '@/lib/data';
import { adaptMetrics, type SystemMetricsRow } from '@/lib/stdb-adapters';
import LineChart from '@/components/charts/LineChart';
import AreaChart from '@/components/charts/AreaChart';

const HISTORY_LEN = 60;

type Histories = {
  cpu: number[];
  mem: number[];
  netTx: number[];
  netRx: number[];
};

function renderServerView(data: SystemMetrics, h: Histories): React.ReactNode {
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
          <div className="chart-card__sub">live · 3s resolution · last {h.cpu.length} samples</div>
        </div>
        <LineChart data={h.cpu.length ? h.cpu : [0]} color="var(--brand-ink)" yMax={100} yLabel="%" fill/>
      </div>

      <div className="chart-card">
        <div className="chart-card__head">
          <div className="chart-card__title">Memory (GB)</div>
          <div className="chart-card__sub">live · ceiling {data.mem.total_gb.toFixed(0)} GB</div>
        </div>
        <LineChart data={h.mem.length ? h.mem : [0]} color="var(--brand-rust)" yMax={data.mem.total_gb} fill/>
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
        <AreaChart tx={h.netTx.length ? h.netTx : [0]} rx={h.netRx.length ? h.netRx : [0]}/>
      </div>
    </div>
  );
}

function useHistories(data: SystemMetrics | null) {
  const cpu = useRef<number[]>([]);
  const mem = useRef<number[]>([]);
  const netTx = useRef<number[]>([]);
  const netRx = useRef<number[]>([]);
  const prevNet = useRef<{ tx: number; rx: number } | null>(null);
  const [, forceRender] = useState(0);

  useEffect(() => {
    if (!data) return;
    const push = (arr: number[], val: number) => {
      arr.push(val);
      if (arr.length > HISTORY_LEN) arr.shift();
    };
    push(cpu.current, data.cpu.pct);
    push(mem.current, data.mem.used_gb);

    const prev = prevNet.current;
    if (prev) {
      push(netTx.current, Math.max(0, (data.net.tx_bytes - prev.tx) / 1e6));
      push(netRx.current, Math.max(0, (data.net.rx_bytes - prev.rx) / 1e6));
    }
    prevNet.current = { tx: data.net.tx_bytes, rx: data.net.rx_bytes };
    forceRender(n => n + 1);
  }, [data]);

  return { cpu: cpu.current, mem: mem.current, netTx: netTx.current, netRx: netRx.current };
}

function ServerLegacy() {
  const { data, loading, error } = usePoll<SystemMetrics>('/system', 3000);
  const histories = useHistories(data);

  if (loading && !data) {
    return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Connecting to admin-api…</div>;
  }
  if (error && !data) {
    return <div className="banner banner--warn" style={{ margin: 0 }}>Failed to reach admin-api: {error}</div>;
  }
  if (!data) return null;

  return renderServerView(data, histories);
}

function ServerStdb() {
  const [metricsRows] = useTable(tables.system_metrics);
  const row = metricsRows[0] as SystemMetricsRow | undefined;
  const data = adaptMetrics(row);
  const histories = useHistories(data);

  if (!row) {
    return <div style={{ padding: 40, color: 'var(--color-fg-muted)', textAlign: 'center' }}>Waiting for the admin-collector worker to publish system_metrics…</div>;
  }
  if (!data) return null;

  return renderServerView(data, histories);
}

export default function Server() {
  if (USE_STDB_ADMIN) return <ServerStdb/>;
  return <ServerLegacy/>;
}
