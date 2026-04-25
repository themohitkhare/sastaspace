// Single shared SpacetimeDB connection for the landing surface.
//
// Bindings (./generated under @sastaspace/stdb-bindings) come from
// `pnpm bindings:generate`. Until they exist (fresh clone, or before the first
// CI module publish), this module returns null and PresencePill renders
// nothing — the rest of the landing is unaffected.

export const STDB_URI =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
export const STDB_MODULE =
  process.env.NEXT_PUBLIC_STDB_MODULE ?? "sastaspace";

type PresenceListener = (count: number) => void;

const listeners = new Set<PresenceListener>();
let lastCount = 0;
let started = false;

function notify(count: number) {
  lastCount = count;
  for (const fn of listeners) fn(count);
}

export function subscribePresence(fn: PresenceListener): () => void {
  listeners.add(fn);
  fn(lastCount);
  if (!started) {
    started = true;
    void start();
  }
  return () => {
    listeners.delete(fn);
  };
}

async function start(): Promise<void> {
  let bindings: Record<string, unknown>;
  try {
    bindings = (await import("@sastaspace/stdb-bindings")) as Record<string, unknown>;
  } catch {
    return; // bindings not generated — pill stays hidden
  }

  const DbConnection = bindings.DbConnection as
    | { builder: () => StdbBuilder }
    | undefined;
  if (!DbConnection) return;

  let conn: StdbConn | null = null;
  conn = DbConnection.builder()
    .withUri(STDB_URI)
    .withDatabaseName(STDB_MODULE)
    .withLightMode(true)
    .onConnect(() => {
      if (!conn) return;
      conn
        .subscriptionBuilder()
        .onApplied(() => notify(countPresence(conn!)))
        .subscribe("SELECT * FROM presence");

      conn.db.presence.onInsert?.(() => notify(countPresence(conn!)));
      conn.db.presence.onDelete?.(() => notify(countPresence(conn!)));
      conn.db.presence.onUpdate?.(() => notify(countPresence(conn!)));
    })
    .onDisconnect(() => notify(0))
    .onConnectError((_ctx: unknown, err: Error) => {
      console.warn("[sastaspace] stdb connect failed:", err?.message ?? err);
    })
    .build();

  // Heartbeat — keeps presence row alive even if disconnect events are unreliable
  const tick = () => {
    if (!conn) return;
    try {
      conn.reducers.heartbeat?.();
    } catch {
      /* ignore */
    }
  };
  if (typeof window !== "undefined") {
    window.setInterval(tick, 20_000);
    window.addEventListener("beforeunload", () => conn?.disconnect());
  }
}

function countPresence(conn: StdbConn): number {
  let n = 0;
  for (const _ of conn.db.presence.iter()) n++;
  return n;
}

// Loose structural types — replaced by real generated types at compile time
// when `packages/stdb-bindings/src/generated/` is populated.
type StdbBuilder = {
  withUri: (uri: string) => StdbBuilder;
  withDatabaseName: (name: string) => StdbBuilder;
  withLightMode: (on: boolean) => StdbBuilder;
  withToken: (t: string) => StdbBuilder;
  onConnect: (fn: (ctx: unknown, identity: unknown, token: string) => void) => StdbBuilder;
  onDisconnect: (fn: () => void) => StdbBuilder;
  onConnectError: (fn: (ctx: unknown, err: Error) => void) => StdbBuilder;
  build: () => StdbConn;
};

type StdbConn = {
  db: {
    presence: {
      iter: () => Iterable<unknown>;
      onInsert?: (fn: () => void) => void;
      onDelete?: (fn: () => void) => void;
      onUpdate?: (fn: () => void) => void;
    };
  };
  reducers: { heartbeat?: () => void };
  subscriptionBuilder: () => {
    onApplied: (fn: () => void) => any;
    subscribe: (q: string) => unknown;
  };
  disconnect: () => void;
};
