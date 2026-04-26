// STDB row → legacy view-shape adapters. Keeps the panel render JSX unchanged
// while the underlying data source flips between HTTP poll and STDB
// subscriptions during the Phase 2/3 cutover.

import type { SystemMetrics, ContainerRow } from '@/lib/data';

// Shape of one row of the `system_metrics` table (id=0 single-row).
export type SystemMetricsRow = {
  cpuPct: number;
  cores: number;
  memUsedGb: number;
  memTotalGb: number;
  memPct: number;
  swapUsedMb: number;
  swapTotalMb: number;
  diskUsedGb: number;
  diskTotalGb: number;
  diskPct: number;
  netTxBytes: bigint;
  netRxBytes: bigint;
  uptimeS: bigint;
  gpuPct?: number | null | undefined;
  gpuVramUsedMb?: number | null | undefined;
  gpuVramTotalMb?: number | null | undefined;
  gpuTempC?: number | null | undefined;
  gpuModel?: string | null | undefined;
};

export type ContainerStatusRow = {
  name: string;
  status: string;
  image: string;
  uptimeS: bigint;
  memUsedMb: number;
  memLimitMb: number;
  restartCount: number;
};

export function adaptMetrics(row: SystemMetricsRow | undefined): SystemMetrics | null {
  if (!row) return null;
  return {
    cpu: { pct: Math.round(row.cpuPct), cores: row.cores },
    mem: {
      used_gb: row.memUsedGb,
      total_gb: row.memTotalGb,
      pct: row.memPct,
      swap_used_mb: row.swapUsedMb,
      swap_total_mb: row.swapTotalMb,
    },
    disk: {
      used_gb: row.diskUsedGb,
      total_gb: row.diskTotalGb,
      pct: row.diskPct,
      mount: '/',
    },
    net: {
      tx_bytes: Number(row.netTxBytes),
      rx_bytes: Number(row.netRxBytes),
    },
    uptime_s: Number(row.uptimeS),
    gpu: row.gpuPct != null
      ? {
          pct: row.gpuPct,
          vram_used_mb: row.gpuVramUsedMb ?? 0,
          vram_total_mb: row.gpuVramTotalMb ?? 0,
          temp_c: row.gpuTempC ?? 0,
          model: row.gpuModel ?? 'unknown',
        }
      : undefined,
  };
}

export function adaptContainers(rows: readonly ContainerStatusRow[]): ContainerRow[] {
  return rows.map(r => ({
    name: r.name,
    status: r.status,
    image: r.image,
    started_at: '',
    uptime_s: Number(r.uptimeS),
    mem_usage_mb: r.memUsedMb,
    mem_limit_mb: r.memLimitMb,
    restart_count: r.restartCount,
  }));
}
