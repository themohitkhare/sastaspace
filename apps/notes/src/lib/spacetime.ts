// Single shared SpacetimeDB connection helper for the notes surface.
// Mirrors apps/landing/src/lib/spacetime.ts — same dynamic-load pattern,
// same env-var defaults, same graceful-no-bindings behaviour.

export const STDB_URI =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
export const STDB_MODULE =
  process.env.NEXT_PUBLIC_STDB_MODULE ?? "sastaspace";

let connectionPromise: Promise<StdbConn | null> | null = null;

export function getConnection(): Promise<StdbConn | null> {
  if (connectionPromise) return connectionPromise;
  connectionPromise = (async () => {
    let bindings: Record<string, unknown>;
    try {
      bindings = (await import("@sastaspace/stdb-bindings")) as Record<string, unknown>;
    } catch {
      return null;
    }
    const DbConnection = bindings.DbConnection as
      | { builder: () => StdbBuilder }
      | undefined;
    if (!DbConnection) return null;

    return new Promise<StdbConn>((resolve, reject) => {
      const conn = DbConnection.builder()
        .withUri(STDB_URI)
        .withDatabaseName(STDB_MODULE)
        .withLightMode(true)
        .onConnect(() => resolve(conn))
        .onConnectError((_ctx: unknown, err: Error) => reject(err))
        .build();
    });
  })();
  return connectionPromise;
}

// Loose structural types — replaced by real generated types at compile time.
export type StdbBuilder = {
  withUri: (uri: string) => StdbBuilder;
  withDatabaseName: (name: string) => StdbBuilder;
  withLightMode: (on: boolean) => StdbBuilder;
  withToken: (t: string) => StdbBuilder;
  onConnect: (fn: () => void) => StdbBuilder;
  onDisconnect: (fn: () => void) => StdbBuilder;
  onConnectError: (fn: (ctx: unknown, err: Error) => void) => StdbBuilder;
  build: () => StdbConn;
};

export type StdbConn = {
  db: {
    comment: {
      iter: () => Iterable<unknown>;
      onInsert?: (fn: () => void) => void;
      onDelete?: (fn: () => void) => void;
      onUpdate?: (fn: () => void) => void;
    };
  };
  reducers: Record<string, unknown>;
  subscriptionBuilder: () => {
    onApplied: (fn: () => void) => any;
    subscribe: (q: string) => unknown;
  };
  disconnect: () => void;
};
