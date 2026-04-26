export type CommentStatus = 'pending' | 'flagged' | 'approved' | 'rejected';
export type ServiceStatus = 'running' | 'unhealthy' | 'stopped' | 'starting';

export type Comment = {
  id: string;
  status: CommentStatus;
  author: string;
  post: string;
  body: string;
  createdAt: string;
};

export type Service = {
  container: string;
  name: string;
  status: ServiceStatus;
  uptime: string;
  uptimeMin: number;
  mem: string;
  memBytes: number;
  image: string;
};

export type Legion = {
  id: string;
  name: string;
  color: string;
  regions: number;
  damage: number;
  players: number;
};

export type Region = {
  id: number;
  name: string;
  legion: string;
  legionColor: string;
  hp: number;
  hpMax: number;
  contested?: boolean;
};

export type Battle = {
  player: string;
  legion: string;
  legionColor: string;
  region: string;
  startedSec: number;
  words: number;
  damage: number;
};

export type LogLine = {
  ts: string;
  text: string;
  level?: string;
};

export type SystemMetrics = {
  cpu: { pct: number; cores: number };
  mem: { used_gb: number; total_gb: number; pct: number; swap_used_mb: number; swap_total_mb: number };
  disk: { used_gb: number; total_gb: number; pct: number; mount: string };
  gpu?: { pct: number; vram_used_mb: number; vram_total_mb: number; temp_c: number; model: string };
  net: { tx_bytes: number; rx_bytes: number };
  uptime_s: number;
};

export type ContainerRow = {
  name: string;
  status: string;
  image: string;
  started_at: string;
  uptime_s: number;
  mem_usage_mb: number;
  mem_limit_mb: number;
  restart_count: number;
};

export const relTime = (iso: string): string => {
  const diff = (Date.now() - new Date(iso).getTime()) / 1000;
  if (diff < 60) return `${Math.floor(diff)}s ago`;
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
};

export function formatUptime(seconds: number): string {
  if (seconds <= 0) return '0s';
  const d = Math.floor(seconds / 86400);
  const h = Math.floor((seconds % 86400) / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  if (d > 0) return `${d}d ${h}h ${m}m`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

// Legion color palette — stable across all TypeWars regions
export const LEGION_COLORS: Record<number, string> = {
  0: '#c05621',
  1: '#4a7c3f',
  2: '#3a6280',
  3: '#3a3633',
  4: '#8a3d14',
};

export const LEGION_NAMES: Record<number, string> = {
  0: 'Crimson Tide',
  1: 'Verdant Pact',
  2: 'Azure Order',
  3: 'Obsidian Cabal',
  4: 'Ember Crown',
};
