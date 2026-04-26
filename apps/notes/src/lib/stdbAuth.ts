// STDB-native auth helpers. Used when NEXT_PUBLIC_USE_STDB_AUTH=true.
// The legacy FastAPI path lives in lib/auth.ts and is unchanged.
//
// Flow:
//   - mintAnonymousIdentity() POSTs to {STDB_HTTP}/v1/identity to get a fresh
//     identity + JWT pair. The JWT authenticates the WS connection that
//     follows.
//   - connectWithToken(token) builds a one-shot DbConnection bound to that
//     JWT and resolves once onConnect fires.
//   - requestMagicLinkViaStdb(email) wires those two together and calls the
//     typed reducer `request_magic_link` from the regenerated bindings.
//   - verifyTokenViaStdb(token) does the same dance and calls `verify_token`,
//     returning the JWT we just bound the connection to — that's the
//     "session token" the verify page persists.
//
// SDK note (2.1.0): conn.reducers.<name>(args) returns Promise<void> that
// resolves when the host acknowledges Ok and rejects with SenderError on Err.
// We don't need the onSuccess/onFailure event-bus pattern here.

const STDB_WS =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
const STDB_HTTP =
  process.env.NEXT_PUBLIC_STDB_HTTP ?? "https://stdb.sastaspace.com";
const STDB_MODULE =
  process.env.NEXT_PUBLIC_STDB_MODULE ?? "sastaspace";

const VERIFY_CALLBACK =
  process.env.NEXT_PUBLIC_NOTES_VERIFY_URL ??
  "https://notes.sastaspace.com/auth/verify";

/** POST /v1/identity → mints a fresh anonymous identity + JWT. */
export async function mintAnonymousIdentity(): Promise<{
  identity: string;
  token: string;
}> {
  const r = await fetch(`${STDB_HTTP}/v1/identity`, { method: "POST" });
  if (!r.ok) {
    throw new Error(`mintAnonymousIdentity: HTTP ${r.status}`);
  }
  const body = (await r.json()) as { identity?: string; token?: string };
  if (!body.token || !body.identity) {
    throw new Error("mintAnonymousIdentity: missing identity/token in response");
  }
  return { identity: body.identity, token: body.token };
}

// Loose structural types for the connection — matches the pattern in
// apps/notes/src/lib/spacetime.ts so we don't need to add a hard dep on
// @sastaspace/stdb-bindings to the runtime bundle. The path alias in
// tsconfig.json makes the dynamic import resolve at typecheck time.
type StdbBuilder = {
  withUri: (uri: string) => StdbBuilder;
  withDatabaseName: (name: string) => StdbBuilder;
  withModuleName?: (name: string) => StdbBuilder;
  withToken: (t: string) => StdbBuilder;
  withLightMode?: (on: boolean) => StdbBuilder;
  onConnect: (fn: () => void) => StdbBuilder;
  onConnectError: (fn: (ctx: unknown, err: Error) => void) => StdbBuilder;
  build: () => StdbConn;
};

type ReducerFn = (params: Record<string, unknown>) => Promise<void>;

type StdbConn = {
  reducers: Record<string, ReducerFn | undefined>;
  disconnect: () => void;
};

/** Build a one-shot connection bound to the given JWT. Resolves on onConnect. */
export async function connectWithToken(token: string): Promise<StdbConn> {
  let bindings: Record<string, unknown>;
  try {
    bindings = (await import("@sastaspace/stdb-bindings")) as Record<
      string,
      unknown
    >;
  } catch (err) {
    throw new Error(
      `stdb bindings not loaded: ${err instanceof Error ? err.message : String(err)}`,
    );
  }
  const DbConnection = bindings.DbConnection as
    | { builder: () => StdbBuilder }
    | undefined;
  if (!DbConnection) throw new Error("DbConnection missing from bindings");

  return new Promise<StdbConn>((resolve, reject) => {
    const builder = DbConnection.builder()
      .withUri(STDB_WS)
      .withDatabaseName(STDB_MODULE)
      .withToken(token);
    if (typeof builder.withLightMode === "function") {
      builder.withLightMode(true);
    }
    const conn = builder
      .onConnect(() => resolve(conn))
      .onConnectError((_ctx, err) => reject(err))
      .build();
  });
}

/**
 * Look up a reducer by either its camelCase or snake_case accessor name.
 * Generated bindings expose the camelCase form (`requestMagicLink`); we tolerate
 * the snake form too in case a future generator change flips the convention.
 */
function pickReducer(
  conn: StdbConn,
  camel: string,
  snake: string,
): ReducerFn {
  const fn = conn.reducers[camel] ?? conn.reducers[snake];
  if (!fn) {
    throw new Error(`reducer ${camel}/${snake} missing on connection`);
  }
  return fn;
}

/**
 * Anonymous flow: mint a throwaway identity, connect, call request_magic_link.
 * Resolves once the host has Ack'd the reducer call (not when email lands).
 */
export async function requestMagicLinkViaStdb(email: string): Promise<void> {
  const { token } = await mintAnonymousIdentity();
  const conn = await connectWithToken(token);
  try {
    const fn = pickReducer(conn, "requestMagicLink", "request_magic_link");
    await fn({
      email,
      app: "notes",
      prevIdentityHex: null,
      callbackUrl: VERIFY_CALLBACK,
    });
  } finally {
    // Best-effort disconnect; the next reconnect will mint a fresh identity.
    try {
      conn.disconnect();
    } catch {
      /* ignore */
    }
  }
}

/**
 * Verify flow: mint identity, connect, call verify_token, return the JWT we
 * just bound the connection to (that's the "session token" callers persist).
 *
 * displayName="" lets the W1 reducer derive the display name from the
 * email's local-part.
 */
export async function verifyTokenViaStdb(token: string): Promise<{
  jwt: string;
  identity: string;
}> {
  const minted = await mintAnonymousIdentity();
  const conn = await connectWithToken(minted.token);
  try {
    const fn = pickReducer(conn, "verifyToken", "verify_token");
    await fn({ token, displayName: "" });
  } finally {
    try {
      conn.disconnect();
    } catch {
      /* ignore */
    }
  }
  return { jwt: minted.token, identity: minted.identity };
}
