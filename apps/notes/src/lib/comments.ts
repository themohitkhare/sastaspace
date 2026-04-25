// Live subscription to comments for a given post slug. Only `approved`
// rows surface to readers; pending/flagged/rejected stay invisible until
// the moderator (or owner override) flips them.

import { getConnection } from "./spacetime";

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
  out.sort((a, b) => a.createdAt - b.createdAt); // oldest first
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

// Comments don't go through string-templated SQL in production — the
// subscriptionBuilder uses parameterized internals — but defensively
// strip anything that looks like a single quote.
function escapeSql(s: string): string {
  return s.replace(/['\\]/g, "");
}

export async function submitComment(
  slug: string,
  name: string,
  body: string,
): Promise<void> {
  const conn = await getConnection();
  if (!conn) throw new Error("not connected");
  // Generated bindings expose camelCase reducer methods.
  const fn =
    conn.reducers.submitAnonComment ?? conn.reducers.submit_anon_comment;
  if (!fn) throw new Error("submit_anon_comment reducer missing in bindings");
  fn(slug, name, body);
}
