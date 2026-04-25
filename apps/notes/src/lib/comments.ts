// Live subscription to comments for a given post slug. Only `approved`
// rows surface to readers; pending/flagged/rejected stay invisible until
// the moderator (or owner override) flips them.
//
// submitComment dispatches to either anon or signed-in flow based on
// whether a session JWT is present in localStorage.

import { getSession } from "./auth";
import { getConnection, STDB_MODULE, STDB_URI } from "./spacetime";

export type Comment = {
  id: number | bigint;
  postSlug: string;
  authorName: string;
  body: string;
  createdAt: number; // ms since epoch
  status: string;
};

type Listener = (comments: readonly Comment[]) => void;

const slugListeners = new Map<string, Set<Listener>>();
const slugSnapshots = new Map<string, readonly Comment[]>();
const subscribed = new Set<string>();

function notify(slug: string, rows: readonly Comment[]) {
  slugSnapshots.set(slug, rows);
  for (const fn of slugListeners.get(slug) ?? []) fn(rows);
}

export function subscribeComments(slug: string, fn: Listener): () => void {
  if (!slugListeners.has(slug)) slugListeners.set(slug, new Set());
  slugListeners.get(slug)!.add(fn);
  fn(slugSnapshots.get(slug) ?? []);

  if (!subscribed.has(slug)) {
    subscribed.add(slug);
    void start(slug);
  }

  return () => {
    slugListeners.get(slug)?.delete(fn);
  };
}

async function start(slug: string): Promise<void> {
  const conn = await getConnection().catch(() => null);
  if (!conn) return;

  const sql = `SELECT * FROM comment WHERE post_slug = '${escapeSql(slug)}' AND status = 'approved'`;
  conn
    .subscriptionBuilder()
    .onApplied(() => notify(slug, snapshot(conn, slug)))
    .subscribe(sql);

  conn.db.comment.onInsert?.(() => notify(slug, snapshot(conn, slug)));
  conn.db.comment.onDelete?.(() => notify(slug, snapshot(conn, slug)));
  conn.db.comment.onUpdate?.(() => notify(slug, snapshot(conn, slug)));
}

function snapshot(
  conn: Awaited<ReturnType<typeof getConnection>>,
  slug: string,
): readonly Comment[] {
  if (!conn) return [];
  const out: Comment[] = [];
  for (const row of conn.db.comment.iter() as Iterable<RawCommentRow>) {
    if (row.postSlug !== slug || row.status !== "approved") continue;
    out.push({
      id: row.id,
      postSlug: row.postSlug,
      authorName: row.authorName,
      body: row.body,
      createdAt: timestampToMs(row.createdAt),
      status: row.status,
    });
  }
  out.sort((a, b) => a.createdAt - b.createdAt);
  return out;
}

type RawCommentRow = {
  id: number | bigint;
  postSlug: string;
  authorName: string;
  body: string;
  createdAt: { __timestamp_micros_since_unix_epoch__?: bigint } | number;
  status: string;
};

function timestampToMs(ts: RawCommentRow["createdAt"]): number {
  if (typeof ts === "number") return ts;
  const micros = ts.__timestamp_micros_since_unix_epoch__;
  if (typeof micros === "bigint") return Number(micros / 1000n);
  return 0;
}

function escapeSql(s: string): string {
  return s.replace(/['\\]/g, "");
}

/** Submit a comment. If signed in, uses submit_user_comment under the
 *  user's own Identity (their JWT); otherwise falls back to anon flow.
 *
 *  Note: the signed-in flow opens a SECOND stdb connection authenticated
 *  with the user's JWT, leaving the page's primary anonymous connection
 *  alone for read subscriptions. The token is short-lived and used once
 *  per submit; we don't keep it open after.
 */
export async function submitComment(
  slug: string,
  name: string,
  body: string,
): Promise<void> {
  const session = getSession();
  if (session) {
    await submitAsUser(slug, body, session.token);
    return;
  }
  const conn = await getConnection();
  if (!conn) throw new Error("not connected");
  const fn =
    conn.reducers.submitAnonComment ?? conn.reducers.submit_anon_comment;
  if (!fn) throw new Error("submit_anon_comment reducer missing");
  fn(slug, name, body);
}

async function submitAsUser(slug: string, body: string, token: string): Promise<void> {
  // Open a dedicated authenticated connection just for this call, then
  // disconnect. We don't pollute the long-lived shared connection with
  // user-specific auth state (the read subscription works fine anonymously).
  let bindings: Record<string, unknown>;
  try {
    bindings = (await import("@sastaspace/stdb-bindings")) as Record<string, unknown>;
  } catch {
    throw new Error("stdb bindings not loaded");
  }
  const DbConnection = bindings.DbConnection as
    | { builder: () => UserConnBuilder }
    | undefined;
  if (!DbConnection) throw new Error("DbConnection missing");

  await new Promise<void>((resolve, reject) => {
    const userConn = DbConnection.builder()
      .withUri(STDB_URI)
      .withDatabaseName(STDB_MODULE)
      .withToken(token)
      .withLightMode(true)
      .onConnect(() => {
        const fn =
          (userConn.reducers as { submitUserComment?: (slug: string, body: string) => void; submit_user_comment?: (slug: string, body: string) => void })
            .submitUserComment ??
          (userConn.reducers as { submit_user_comment?: (slug: string, body: string) => void }).submit_user_comment;
        if (!fn) {
          reject(new Error("submit_user_comment reducer missing"));
          userConn.disconnect();
          return;
        }
        try {
          fn(slug, body);
          resolve();
        } catch (e) {
          reject(e instanceof Error ? e : new Error(String(e)));
        } finally {
          // Give the call a moment to flush before disconnecting.
          setTimeout(() => userConn.disconnect(), 500);
        }
      })
      .onConnectError((_ctx: unknown, err: Error) => reject(err))
      .build();
  });
}

type UserConnBuilder = {
  withUri: (uri: string) => UserConnBuilder;
  withDatabaseName: (name: string) => UserConnBuilder;
  withToken: (t: string) => UserConnBuilder;
  withLightMode: (on: boolean) => UserConnBuilder;
  onConnect: (fn: () => void) => UserConnBuilder;
  onConnectError: (fn: (ctx: unknown, err: Error) => void) => UserConnBuilder;
  build: { reducers: Record<string, unknown>; disconnect: () => void } & ((() => UserConn));
};

type UserConn = {
  reducers: Record<string, unknown>;
  disconnect: () => void;
};
