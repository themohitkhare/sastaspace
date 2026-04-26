import si from "systeminformation";
import Docker from "dockerode";
import { spawn, type ChildProcess } from "node:child_process";
import type { StdbConn } from "../shared/stdb.js";

const log = (level: string, msg: string, extra?: unknown) =>
  console.log(
    JSON.stringify({
      ts: new Date().toISOString(),
      agent: "admin-collector",
      level,
      msg,
      extra,
    }),
  );

const METRICS_INTERVAL_MS = 3_000;
const CONTAINERS_INTERVAL_MS = 15_000;

// Containers the collector watches. Mirror of ALLOWED_CONTAINERS in
// modules/sastaspace/src/lib.rs — keep in sync. (Future: thread this
// through `app_config` so the list lives in one place.)
const ALLOWED_CONTAINERS = [
  "sastaspace-spacetime",
  "sastaspace-ollama",
  "sastaspace-localai",
  "sastaspace-workers",
  "sastaspace-landing",
  "sastaspace-notes",
  "sastaspace-admin",
  "sastaspace-typewars",
  "sastaspace-cloudflared",
  "sastaspace-auth",
  "sastaspace-admin-api",
  "sastaspace-deck",
  "sastaspace-moderator",
];

const LEVEL_RE = /\b(ERROR|WARN|WARNING|DEBUG)\b/i;
export function classifyLevel(line: string): string {
  const m = LEVEL_RE.exec(line);
  if (!m) return "info";
  const w = m[1].toUpperCase();
  if (w === "ERROR") return "error";
  if (w === "WARN" || w === "WARNING") return "warn";
  if (w === "DEBUG") return "debug";
  return "info";
}

interface GpuReading {
  pct?: number;
  vram_used_mb?: number;
  vram_total_mb?: number;
  temp_c?: number;
  model?: string;
}

async function readGpu(): Promise<GpuReading | null> {
  // Try nvidia-smi first; fall back to rocm-smi; tolerate absence.
  try {
    const out = await runCmd(
      "nvidia-smi",
      [
        "--query-gpu=utilization.gpu,memory.used,memory.total,temperature.gpu,name",
        "--format=csv,noheader,nounits",
      ],
      3_000,
    );
    const parts = out.trim().split(",").map((s) => s.trim());
    if (parts.length >= 5) {
      return {
        pct: parseInt(parts[0], 10),
        vram_used_mb: parseInt(parts[1], 10),
        vram_total_mb: parseInt(parts[2], 10),
        temp_c: parseInt(parts[3], 10),
        model: parts[4],
      };
    }
  } catch {
    /* fall through to rocm */
  }
  try {
    const out = await runCmd(
      "rocm-smi",
      ["--showuse", "--showmeminfo", "vram", "--showtemp", "--json"],
      5_000,
    );
    const data = JSON.parse(out) as Record<string, Record<string, unknown>>;
    const card = Object.values(data)[0];
    if (!card) return null;
    const pct = Math.round(
      parseFloat(String(card["GPU use (%)"] ?? card["GPU Use (%)"] ?? 0)),
    );
    const vramUsed = Math.round(
      Number(card["VRAM Total Used Memory (B)"] ?? 0) / (1024 * 1024),
    );
    const vramTotal = Math.round(
      Number(card["VRAM Total Memory (B)"] ?? 0) / (1024 * 1024),
    );
    const temp = Math.round(
      parseFloat(
        String(
          card["Temperature (Sensor edge) (C)"] ?? card["Temperature (C)"] ?? 0,
        ),
      ),
    );
    return {
      pct,
      vram_used_mb: vramUsed,
      vram_total_mb: vramTotal,
      temp_c: temp,
      model: "AMD GPU",
    };
  } catch {
    return null;
  }
}

function runCmd(
  cmd: string,
  args: string[],
  timeoutMs: number,
): Promise<string> {
  return new Promise((resolve, reject) => {
    const p = spawn(cmd, args);
    let out = "";
    let err = "";
    const timer = setTimeout(() => {
      p.kill("SIGKILL");
      reject(new Error(`${cmd} timed out`));
    }, timeoutMs);
    p.stdout?.on("data", (d: Buffer) => {
      out += d.toString();
    });
    p.stderr?.on("data", (d: Buffer) => {
      err += d.toString();
    });
    p.on("error", (e) => {
      clearTimeout(timer);
      reject(e);
    });
    p.on("close", (code) => {
      clearTimeout(timer);
      if (code === 0) resolve(out);
      else reject(new Error(`${cmd} exited ${code}: ${err}`));
    });
  });
}

// ---- Structural types we need from the SDK connection. ----
//
// We avoid importing concrete generated types so this file compiles before
// W1 fills out `connection` on `StdbConn` and before bindings are
// regenerated post-merge. Once those land, the controller's regen step
// will produce strongly-typed accessors and these can be tightened.

interface ReducerNamespace {
  upsertSystemMetrics: (...args: unknown[]) => unknown;
  upsertContainerStatus: (...args: unknown[]) => unknown;
  appendLogEvent: (...args: unknown[]) => unknown;
  pruneLogEvents?: (...args: unknown[]) => unknown;
}

interface LogInterestRow {
  container: string;
}

interface LogInterestTable {
  iter(): Iterable<LogInterestRow>;
  onInsert(handler: (ctx: unknown, row: LogInterestRow) => void): void;
  onDelete(handler: (ctx: unknown, row: LogInterestRow) => void): void;
}

interface DbNamespace {
  logInterest: LogInterestTable;
}

interface SubscriptionBuilder {
  subscribe(queries: string[]): unknown;
}

interface SdkConnection {
  reducers: ReducerNamespace;
  db: DbNamespace;
  subscriptionBuilder(): SubscriptionBuilder;
}

export async function start(db: StdbConn): Promise<() => Promise<void>> {
  const conn = db.connection as SdkConnection;
  const docker = new Docker(); // defaults to /var/run/docker.sock

  // ---- Loop 1: system metrics every 3s ----
  const collectMetrics = async (): Promise<void> => {
    try {
      const [cpu, mem, fs, net, time] = await Promise.all([
        si.currentLoad(),
        si.mem(),
        si.fsSize(),
        si.networkStats(),
        si.time(),
      ]);
      const root = fs.find((f) => f.mount === "/") ?? fs[0];
      const netTotals = net.reduce(
        (acc, n) => ({ tx: acc.tx + n.tx_bytes, rx: acc.rx + n.rx_bytes }),
        { tx: 0, rx: 0 },
      );
      const gpu = await readGpu();
      conn.reducers.upsertSystemMetrics(
        Number((cpu.currentLoad ?? 0).toFixed(1)),
        cpu.cpus?.length ?? 0,
        Number((mem.used / 1e9).toFixed(2)),
        Number((mem.total / 1e9).toFixed(2)),
        Number(((mem.used / mem.total) * 100).toFixed(1)),
        Math.round(mem.swapused / 1e6),
        Math.round(mem.swaptotal / 1e6),
        Math.round((root?.used ?? 0) / 1e9),
        Math.round((root?.size ?? 0) / 1e9),
        Number((root?.use ?? 0).toFixed(1)),
        BigInt(netTotals.tx),
        BigInt(netTotals.rx),
        BigInt(Math.round((time as { uptime?: number }).uptime ?? 0)),
        gpu?.pct ?? null,
        gpu?.vram_used_mb ?? null,
        gpu?.vram_total_mb ?? null,
        gpu?.temp_c ?? null,
        gpu?.model ?? null,
      );
    } catch (e) {
      log("error", "metrics collection failed", { error: String(e) });
    }
  };
  const metricsTimer = setInterval(() => {
    void collectMetrics();
  }, METRICS_INTERVAL_MS);
  void collectMetrics(); // fire immediately

  // ---- Loop 2: container status every 15s ----
  const collectContainers = async (): Promise<void> => {
    try {
      const list = await docker.listContainers({ all: true });
      for (const c of list) {
        const name = (c.Names[0] ?? "").replace(/^\//, "");
        if (!ALLOWED_CONTAINERS.includes(name)) continue;
        const container = docker.getContainer(c.Id);
        const inspect = await container.inspect();
        const state = inspect.State;
        const startedAt = state.StartedAt ? Date.parse(state.StartedAt) : 0;
        const uptimeS =
          state.Status === "running" && startedAt
            ? Math.max(0, Math.floor((Date.now() - startedAt) / 1000))
            : 0;
        let memUsedMb = 0;
        let memLimitMb = 0;
        if (state.Status === "running") {
          try {
            const stats = (await container.stats({ stream: false })) as {
              memory_stats?: { usage?: number; limit?: number };
            };
            memUsedMb = Math.round(
              (stats.memory_stats?.usage ?? 0) / 1_048_576,
            );
            memLimitMb = Math.round(
              (stats.memory_stats?.limit ?? 0) / 1_048_576,
            );
          } catch {
            /* leave at 0 */
          }
        }
        const image = c.Image ?? inspect.Config.Image ?? "";
        const restartCount = inspect.RestartCount ?? 0;
        conn.reducers.upsertContainerStatus(
          name,
          state.Status ?? "unknown",
          image,
          BigInt(uptimeS),
          memUsedMb,
          memLimitMb,
          restartCount,
        );
      }
    } catch (e) {
      log("error", "container collection failed", { error: String(e) });
      // Tolerate docker.sock unavailability — keep collecting metrics.
    }
  };
  const containersTimer = setInterval(() => {
    void collectContainers();
  }, CONTAINERS_INTERVAL_MS);
  void collectContainers(); // fire immediately

  // ---- Loop 3: log streaming driven by log_interest ----
  const logProcesses = new Map<string, ChildProcess>();

  function startTailing(container: string): void {
    if (logProcesses.has(container)) return;
    if (!ALLOWED_CONTAINERS.includes(container)) {
      log("warn", "ignored unknown container in log_interest", { container });
      return;
    }
    log("info", "spawning docker logs subprocess", { container });
    const p = spawn("docker", [
      "logs",
      "--follow",
      "--tail",
      "0",
      container,
    ]);
    let buf = "";
    const onData = (chunk: Buffer): void => {
      buf += chunk.toString();
      const lines = buf.split("\n");
      buf = lines.pop() ?? "";
      for (const line of lines) {
        if (!line) continue;
        const text = line.length > 4000 ? line.slice(0, 4000) : line;
        const level = classifyLevel(text);
        try {
          conn.reducers.appendLogEvent(
            container,
            BigInt(Date.now() * 1000),
            level,
            text,
          );
        } catch (e) {
          log("warn", "appendLogEvent failed", {
            container,
            error: String(e),
          });
        }
      }
    };
    p.stdout?.on("data", onData);
    p.stderr?.on("data", onData);
    p.on("close", (code) => {
      log("info", "docker logs subprocess exited", { container, code });
      logProcesses.delete(container);
    });
    p.on("error", (e) => {
      log("error", "docker logs subprocess errored", {
        container,
        error: String(e),
      });
      logProcesses.delete(container);
    });
    logProcesses.set(container, p);
  }

  function stopTailing(container: string): void {
    const p = logProcesses.get(container);
    if (!p) return;
    log("info", "killing docker logs subprocess", { container });
    p.kill("SIGTERM");
    logProcesses.delete(container);
  }

  function refreshSubscriptions(): void {
    const wanted = new Set<string>();
    for (const row of conn.db.logInterest.iter()) {
      wanted.add(row.container);
    }
    // Spawn missing.
    for (const c of wanted) startTailing(c);
    // Kill orphans.
    for (const c of [...logProcesses.keys()]) {
      if (!wanted.has(c)) stopTailing(c);
    }
  }

  conn.subscriptionBuilder().subscribe(["SELECT * FROM log_interest"]);
  conn.db.logInterest.onInsert((_ctx, row) => {
    startTailing(row.container);
  });
  conn.db.logInterest.onDelete((_ctx, _row) => {
    refreshSubscriptions();
  });

  // Drain any pre-existing interest rows on boot.
  refreshSubscriptions();

  log("info", "admin-collector started");

  return async () => {
    log("info", "admin-collector stopping");
    clearInterval(metricsTimer);
    clearInterval(containersTimer);
    for (const [c, p] of logProcesses) {
      log("info", "killing log subprocess on shutdown", { container: c });
      p.kill("SIGTERM");
    }
    logProcesses.clear();
  };
}
