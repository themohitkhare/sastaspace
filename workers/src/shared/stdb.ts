// SpacetimeDB connection wrapper for the workers process.
//
// Phase 1 W1 fleshed this out. The shape is intentionally minimal: each agent
// pulls the typed `connection.db.<table>` and `connection.reducers.<name>`
// accessors directly off the underlying connection via the `connection` field
// (using structural casts until the generated bindings know about each
// agent's tables). The `callReducer` / `subscribe` overloads on the wrapper
// are escape hatches for ad-hoc / dynamic call sites (tests, smoke scripts).
//
// Why we don't `import { DbConnection } from "@sastaspace/stdb-bindings"`:
// the Phase 0 generated bindings index doesn't currently typecheck under
// NodeNext (extension-less re-exports + drift between the bindings cli and
// the runtime SDK). Coordination rules say the controller will regenerate
// bindings once after all Phase 1 workstreams merge — until that happens,
// importing them blows up `tsc --noEmit`. We use a dynamic `import()` of the
// generated DbConnection at runtime so this file stays type-safe at compile
// time, and the worker fails loudly at boot if the bindings are missing or
// shape-incompatible.
//
// SDK API note: the `spacetimedb` 2.1 builder is `withDatabaseName` (not
// `withModuleName` as an earlier draft of the plan said). Discovered from
// the SDK typings + the existing landing `lib/spacetime.ts`.

// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type StdbConnection = any;

export interface StdbConn {
  connection: StdbConnection;
  callReducer(name: string, ...args: unknown[]): Promise<void>;
  subscribe(query: string): Promise<void>;
  close(): Promise<void>;
}

interface DbConnectionLike {
  builder: () => DbConnectionBuilderLike;
}

interface DbConnectionBuilderLike {
  withUri: (uri: string) => DbConnectionBuilderLike;
  withDatabaseName: (name: string) => DbConnectionBuilderLike;
  withToken: (token: string) => DbConnectionBuilderLike;
  onConnect: (
    cb: (conn: StdbConnection, ...rest: unknown[]) => void,
  ) => DbConnectionBuilderLike;
  onConnectError: (cb: (ctx: unknown, err: Error) => void) => DbConnectionBuilderLike;
  build: () => StdbConnection;
}

export async function connect(
  url: string,
  module: string,
  token: string,
): Promise<StdbConn> {
  const wsUrl = url.replace(/^http(s?):\/\//, "ws$1://");

  // Use a non-literal specifier so `tsc --noEmit` doesn't try to resolve and
  // type-check the bindings package, which has Phase 0 typing issues that the
  // post-merge regen will fix. The runtime module specifier is unchanged.
  const bindingsSpec = "@sastaspace/stdb-bindings";
  const bindings = (await import(bindingsSpec)) as unknown as {
    DbConnection?: DbConnectionLike;
  };
  const DbConnection = bindings.DbConnection;
  if (!DbConnection || typeof DbConnection.builder !== "function") {
    throw new Error(
      "@sastaspace/stdb-bindings does not export a DbConnection builder — " +
        "regenerate bindings via `pnpm bindings:generate`",
    );
  }

  const connection = await new Promise<StdbConnection>((resolve, reject) => {
    DbConnection.builder()
      .withUri(wsUrl)
      .withDatabaseName(module)
      .withToken(token)
      .onConnect((conn) => resolve(conn))
      .onConnectError((_ctx, err) => reject(err))
      .build();
  });

  return {
    connection,
    async callReducer(name, ...args) {
      const reducers = connection.reducers as unknown as Record<
        string,
        (...a: unknown[]) => unknown
      >;
      const fn = reducers[name];
      if (typeof fn !== "function") {
        throw new Error(`unknown reducer ${name}`);
      }
      const result = fn(...args);
      if (result instanceof Promise) {
        await result;
      }
    },
    async subscribe(query) {
      connection.subscriptionBuilder().subscribe([query]);
    },
    async close() {
      connection.disconnect();
    },
  };
}
