// auth-mailer (Phase 1 W1) — drains the `pending_email` STDB table by sending
// the queued message via Resend, then calls `mark_email_sent` /
// `mark_email_failed` to close out the row.
//
// Subscribes to `SELECT * FROM pending_email WHERE status = 'queued'`. On every
// insert (and on startup, for any rows that pre-existed the connection) it
// sends through Resend and reports the outcome back as a reducer call.
//
// Note on bindings: the `pendingEmail` table accessor and the
// `markEmailSent`/`markEmailFailed` reducer wrappers are produced by
// `spacetime generate --lang typescript`. The controller regenerates bindings
// once after all Phase 1 workstreams merge (per the W1 coordination rules),
// so until that happens the typed accessors won't exist on the generated
// `DbConnection`. We reach through `as Record<...>` casts so this file
// compiles against the Phase 0 bindings; once regen lands, the types align
// for free without any source changes here.

import { Resend } from "resend";
import { env } from "../shared/env.js";
import type { StdbConn } from "../shared/stdb.js";

type PendingEmailRow = {
  id: bigint;
  toEmail: string;
  subject: string;
  bodyHtml: string;
  bodyText: string;
  status: string;
};

type ReducerCallback = (...args: unknown[]) => unknown;

type PendingEmailAccessor = {
  iter: () => Iterable<PendingEmailRow>;
  onInsert: (cb: (ctx: unknown, row: PendingEmailRow) => void) => void;
};

const log = (level: string, msg: string, extra?: unknown) =>
  console.log(
    JSON.stringify({
      ts: new Date().toISOString(),
      agent: "auth-mailer",
      level,
      msg,
      extra,
    }),
  );

export async function start(db: StdbConn): Promise<() => Promise<void>> {
  if (!env.RESEND_API_KEY) {
    throw new Error("auth-mailer enabled but RESEND_API_KEY missing");
  }
  const resend = new Resend(env.RESEND_API_KEY);

  const conn = db.connection;

  // Re-typed accessors. After bindings regen these will be the typed
  // generated names; until then we reach through the `unknown` cast.
  const dbView = conn.db as unknown as { pendingEmail: PendingEmailAccessor };
  const reducers = conn.reducers as unknown as {
    markEmailSent: ReducerCallback;
    markEmailFailed: ReducerCallback;
  };

  conn
    .subscriptionBuilder()
    .subscribe(["SELECT * FROM pending_email WHERE status = 'queued'"]);

  const inFlight = new Set<string>();

  const handleRow = async (row: PendingEmailRow) => {
    const idKey = row.id.toString();
    if (inFlight.has(idKey)) return;
    inFlight.add(idKey);
    try {
      const sendResult = await resend.emails.send({
        from: env.RESEND_FROM,
        to: [row.toEmail],
        subject: row.subject,
        html: row.bodyHtml,
        text: row.bodyText,
      });
      if (sendResult.error) {
        log("warn", "resend rejected", {
          id: idKey,
          error: sendResult.error,
        });
        await Promise.resolve(
          reducers.markEmailFailed(
            row.id,
            JSON.stringify(sendResult.error).slice(0, 400),
          ),
        );
      } else {
        log("info", "email sent", {
          id: idKey,
          msg_id: sendResult.data?.id,
        });
        await Promise.resolve(
          reducers.markEmailSent(row.id, sendResult.data?.id ?? "unknown"),
        );
      }
    } catch (e) {
      log("error", "resend threw", { id: idKey, error: String(e) });
      try {
        await Promise.resolve(
          reducers.markEmailFailed(row.id, String(e).slice(0, 400)),
        );
      } catch (reportErr) {
        log("error", "mark_email_failed reducer failed", {
          id: idKey,
          error: String(reportErr),
        });
      }
    } finally {
      inFlight.delete(idKey);
    }
  };

  dbView.pendingEmail.onInsert((_ctx, row) => {
    if (row.status === "queued") void handleRow(row);
  });

  // Drain anything that was queued before we wired the subscription.
  for (const row of dbView.pendingEmail.iter()) {
    if (row.status === "queued") void handleRow(row);
  }

  log("info", "auth-mailer started");

  return async () => {
    log("info", "auth-mailer stopping");
  };
}
