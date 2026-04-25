// Admin-only helpers used by /admin/comments. The owner identity is the
// SAME hex constant as in the module (module/src/lib.rs OWNER_HEX). When
// the signed-in session's identity matches, the admin queue unlocks.
//
// We can't read the user's stdb Identity from a JWT without fully decoding
// it, but the auth callback already saved the email; we treat the email
// match against OWNER_EMAIL as the gate. Combined with the module-level
// owner check on set_comment_status (which IS based on Identity), this is
// defense-in-depth: even if the UI guard fails, the reducer rejects the
// call with "not authorized".

import { getSession } from "./auth";
import { STDB_MODULE, STDB_URI } from "./spacetime";

// Configurable so a different owner email can be set without recompiling
// (defaults to mohitkhare582 from the brand bio).
const OWNER_EMAIL =
  process.env.NEXT_PUBLIC_OWNER_EMAIL ?? "mohitkhare582@gmail.com";

export type AdminComment = {
  id: number | bigint;
  postSlug: string;
  authorName: string;
  body: string;
  createdAt: number;
  status: "pending" | "approved" | "flagged" | "rejected";
};

export function isOwnerSignedIn(): boolean {
  const session = getSession();
  if (!session) return false;
  return session.email.toLowerCase() === OWNER_EMAIL.toLowerCase();
}

/** Subscribe to ALL comments (every status) — only call from /admin/comments. */
export function subscribeAdminComments(
  fn: (rows: readonly AdminComment[]) => void,
): () => void {
  let active = true;
  let teardown: (() => void) | undefined;

  void (async () => {
    let bindings: Record<string, unknown>;
    try {
      bindings = (await import("@sastaspace/stdb-bindings")) as Record<string, unknown>;
    } catch {
      return;
    }
    if (!active) return;

    const DbConnection = bindings.DbConnection as
      | { builder: () => AdminBuilder }
      | undefined;
    if (!DbConnection) return;

    const session = getSession();
    if (!session) return;

    const conn = DbConnection.builder()
      .withUri(STDB_URI)
      .withDatabaseName(STDB_MODULE)
      .withToken(session.token)
      .withLightMode(true)
      .onConnect(() => {
        conn
          .subscriptionBuilder()
          .onApplied(() => fn(snapshot(conn)))
          .subscribe("SELECT * FROM comment");

        conn.db.comment.onInsert?.(() => fn(snapshot(conn)));
        conn.db.comment.onDelete?.(() => fn(snapshot(conn)));
        conn.db.comment.onUpdate?.(() => fn(snapshot(conn)));
      })
      .onConnectError((_ctx: unknown, err: Error) => {
        console.warn("[admin] connect error:", err?.message);
      })
      .build();

    teardown = () => conn.disconnect();
  })();

  return () => {
    active = false;
    teardown?.();
  };
}

function snapshot(conn: AdminConn): readonly AdminComment[] {
  const out: AdminComment[] = [];
  for (const row of conn.db.comment.iter() as Iterable<RawRow>) {
    out.push({
      id: row.id,
      postSlug: row.postSlug,
      authorName: row.authorName,
      body: row.body,
      createdAt: tsToMs(row.createdAt),
      status: (row.status as AdminComment["status"]) ?? "pending",
    });
  }
  // Pending + flagged first (need attention), then by created_at desc
  out.sort((a, b) => {
    const needsAttn = (s: string) => (s === "pending" || s === "flagged" ? 0 : 1);
    const ord = needsAttn(a.status) - needsAttn(b.status);
    if (ord !== 0) return ord;
    return b.createdAt - a.createdAt;
  });
  return out;
}

type RawRow = {
  id: number | bigint;
  postSlug: string;
  authorName: string;
  body: string;
  createdAt: { __timestamp_micros_since_unix_epoch__?: bigint } | number;
  status: string;
};

function tsToMs(ts: RawRow["createdAt"]): number {
  if (typeof ts === "number") return ts;
  const m = ts.__timestamp_micros_since_unix_epoch__;
  return typeof m === "bigint" ? Number(m / 1000n) : 0;
}

export async function setStatus(
  id: number | bigint,
  status: AdminComment["status"],
): Promise<void> {
  await callOwnerReducer("set_comment_status", [Number(id), status]);
}

export async function deleteComment(id: number | bigint): Promise<void> {
  await callOwnerReducer("delete_comment", [Number(id)]);
}

async function callOwnerReducer(name: string, args: unknown[]): Promise<void> {
  const session = getSession();
  if (!session) throw new Error("not signed in");

  // Open a short-lived owner-authenticated connection and call the reducer.
  let bindings: Record<string, unknown>;
  try {
    bindings = (await import("@sastaspace/stdb-bindings")) as Record<string, unknown>;
  } catch {
    throw new Error("bindings unavailable");
  }
  const DbConnection = bindings.DbConnection as
    | { builder: () => AdminBuilder }
    | undefined;
  if (!DbConnection) throw new Error("DbConnection missing");

  await new Promise<void>((resolve, reject) => {
    const conn = DbConnection.builder()
      .withUri(STDB_URI)
      .withDatabaseName(STDB_MODULE)
      .withToken(session.token)
      .withLightMode(true)
      .onConnect(() => {
        try {
          const reducers = conn.reducers as Record<string, (...args: unknown[]) => void>;
          const camel = name.replace(/_(\w)/g, (_m, c) => c.toUpperCase());
          const fn = reducers[camel] ?? reducers[name];
          if (!fn) {
            reject(new Error(`reducer ${name} missing in bindings`));
            return;
          }
          fn(...args);
          resolve();
        } catch (e) {
          reject(e instanceof Error ? e : new Error(String(e)));
        } finally {
          setTimeout(() => conn.disconnect(), 500);
        }
      })
      .onConnectError((_ctx: unknown, err: Error) => reject(err))
      .build();
  });
}

type AdminBuilder = {
  withUri: (u: string) => AdminBuilder;
  withDatabaseName: (n: string) => AdminBuilder;
  withToken: (t: string) => AdminBuilder;
  withLightMode: (b: boolean) => AdminBuilder;
  onConnect: (fn: () => void) => AdminBuilder;
  onConnectError: (fn: (ctx: unknown, err: Error) => void) => AdminBuilder;
  build: () => AdminConn;
};

type AdminConn = {
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
