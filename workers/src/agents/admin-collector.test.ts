import { describe, it, expect, vi, beforeEach } from "vitest";
import { EventEmitter } from "node:events";

// ---- Mock systeminformation ----
vi.mock("systeminformation", () => ({
  default: {
    currentLoad: vi
      .fn()
      .mockResolvedValue({ currentLoad: 12.34, cpus: new Array(8).fill({}) }),
    mem: vi.fn().mockResolvedValue({
      used: 4e9,
      total: 16e9,
      swapused: 0,
      swaptotal: 2e9,
    }),
    fsSize: vi
      .fn()
      .mockResolvedValue([{ mount: "/", used: 100e9, size: 500e9, use: 20.0 }]),
    networkStats: vi.fn().mockResolvedValue([{ tx_bytes: 1, rx_bytes: 2 }]),
    time: vi.fn().mockResolvedValue({ uptime: 12345 }),
  },
}));

// ---- Mock dockerode ----
const fakeContainer = (name: string) => ({
  Id: `id-${name}`,
  Names: [`/${name}`],
  Image: "img:latest",
});
const dockerListMock = vi
  .fn()
  .mockResolvedValue([fakeContainer("sastaspace-spacetime")]);
const dockerInspectMock = vi.fn().mockResolvedValue({
  State: {
    Status: "running",
    StartedAt: new Date(Date.now() - 60_000).toISOString(),
  },
  Config: { Image: "img:latest" },
  RestartCount: 0,
});
const dockerStatsMock = vi.fn().mockResolvedValue({
  memory_stats: { usage: 1_048_576 * 50, limit: 1_048_576 * 200 },
});
vi.mock("dockerode", () => ({
  default: vi.fn().mockImplementation(() => ({
    listContainers: dockerListMock,
    getContainer: () => ({
      inspect: dockerInspectMock,
      stats: dockerStatsMock,
    }),
  })),
}));

// ---- Mock child_process so we can drive log subprocess lifecycle. ----
type FakeProc = EventEmitter & {
  stdout: EventEmitter;
  stderr: EventEmitter;
  kill: ReturnType<typeof vi.fn>;
};
const spawned: Array<{ cmd: string; args: string[]; emitter: FakeProc }> = [];
vi.mock("node:child_process", () => ({
  spawn: vi.fn().mockImplementation((cmd: string, args: string[]) => {
    const stdout = new EventEmitter();
    const stderr = new EventEmitter();
    const proc = Object.assign(new EventEmitter(), {
      stdout,
      stderr,
      kill: vi.fn(),
    }) as FakeProc;
    spawned.push({ cmd, args, emitter: proc });
    // GPU probes (`nvidia-smi`, `rocm-smi`) must complete promptly or the
    // metrics loop hangs awaiting `readGpu()`. We synthesise a non-zero
    // exit so both probes "fail" and the agent records null GPU fields.
    if (cmd === "nvidia-smi" || cmd === "rocm-smi") {
      setImmediate(() => {
        proc.emit("close", 1);
      });
    }
    // `docker logs --follow ...` stays alive until we manually drive it.
    return proc;
  }),
}));

vi.mock("../shared/env.js", () => ({
  env: { WORKER_ADMIN_COLLECTOR_ENABLED: true },
}));

// ---- shared fake STDB ----

interface FakeRow {
  container: string;
  subscriber: string;
  created_at: number;
}

function makeFakeDb() {
  const interestRows: FakeRow[] = [];
  const interestInsertHandlers: Array<
    (ctx: unknown, r: FakeRow) => void
  > = [];
  const interestDeleteHandlers: Array<
    (ctx: unknown, r: FakeRow) => void
  > = [];
  const reducers = {
    upsertSystemMetrics: vi.fn(),
    upsertContainerStatus: vi.fn(),
    appendLogEvent: vi.fn(),
  };
  return {
    interestRows,
    interestInsertHandlers,
    interestDeleteHandlers,
    reducers,
    conn: {
      subscriptionBuilder: () => ({ subscribe: vi.fn() }),
      reducers,
      db: {
        logInterest: {
          iter: () => interestRows,
          onInsert: (cb: (c: unknown, r: FakeRow) => void) => {
            interestInsertHandlers.push(cb);
          },
          onDelete: (cb: (c: unknown, r: FakeRow) => void) => {
            interestDeleteHandlers.push(cb);
          },
        },
      },
    },
  };
}

describe("admin-collector", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    spawned.length = 0;
    dockerListMock.mockResolvedValue([fakeContainer("sastaspace-spacetime")]);
  });

  it("happy path: metrics + container loops fire and call upsert reducers", async () => {
    const fake = makeFakeDb();
    const { start } = await import("./admin-collector.js");
    const stop = await start({
      connection: fake.conn,
      callReducer: vi.fn(),
      subscribe: vi.fn(),
      close: vi.fn(),
    } as never);
    // Let initial collectMetrics + collectContainers settle.
    await new Promise((r) => setTimeout(r, 100));
    expect(fake.reducers.upsertSystemMetrics).toHaveBeenCalled();
    expect(fake.reducers.upsertContainerStatus).toHaveBeenCalled();
    // SDK 2.1: reducers are called with a single object literal (not positional args).
    const args = fake.reducers.upsertSystemMetrics.mock.calls[0];
    expect(args[0]).toMatchObject({ cores: 8 }); // object shape check
    await stop();
  });

  it("log_interest add spawns subprocess; remove kills it", async () => {
    const fake = makeFakeDb();
    const { start } = await import("./admin-collector.js");
    const stop = await start({
      connection: fake.conn,
      callReducer: vi.fn(),
      subscribe: vi.fn(),
      close: vi.fn(),
    } as never);
    // Filter out spawns that are not docker-logs (e.g. nvidia-smi probe).
    const dockerSpawns = () =>
      spawned.filter(
        (s) =>
          s.cmd === "docker" &&
          s.args.includes("logs") &&
          s.args.includes("--follow"),
      );
    expect(dockerSpawns().length).toBe(0);
    // Simulate add_log_interest landing on the client.
    fake.interestRows.push({
      container: "sastaspace-spacetime",
      subscriber: "alice",
      created_at: 1,
    });
    fake.interestInsertHandlers.forEach((h) => h(null, fake.interestRows[0]));
    expect(
      dockerSpawns().some((s) => s.args.includes("sastaspace-spacetime")),
    ).toBe(true);
    // Drive a log line through stdout — should call appendLogEvent.
    const proc = dockerSpawns()[0].emitter;
    proc.stdout.emit("data", Buffer.from("hello world ERROR boom\n"));
    expect(fake.reducers.appendLogEvent).toHaveBeenCalled();
    // SDK 2.1: called with a single object literal (not positional args).
    const callArgs = fake.reducers.appendLogEvent.mock.calls[0];
    expect(callArgs[0]).toMatchObject({ container: "sastaspace-spacetime", level: "error" });
    // Now simulate remove_log_interest deleting the only row.
    fake.interestRows.length = 0;
    fake.interestDeleteHandlers.forEach((h) =>
      h(null, {
        container: "sastaspace-spacetime",
        subscriber: "alice",
        created_at: 1,
      }),
    );
    expect(proc.kill).toHaveBeenCalledWith("SIGTERM");
    await stop();
  });

  it("docker.sock unavailable: container loop logs error, metrics keep flowing", async () => {
    dockerListMock.mockRejectedValueOnce(
      new Error("EACCES /var/run/docker.sock"),
    );
    const fake = makeFakeDb();
    const { start } = await import("./admin-collector.js");
    const stop = await start({
      connection: fake.conn,
      callReducer: vi.fn(),
      subscribe: vi.fn(),
      close: vi.fn(),
    } as never);
    await new Promise((r) => setTimeout(r, 100));
    // Metrics still upserted.
    expect(fake.reducers.upsertSystemMetrics).toHaveBeenCalled();
    // Container upsert NOT called (the error path skipped it).
    expect(fake.reducers.upsertContainerStatus).not.toHaveBeenCalled();
    await stop();
  });
});
