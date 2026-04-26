"use client";

// Phase 2 F4 — Subscribe-first reducer-call helpers for the /lab/deck page.
//
// `request_plan` and `request_generate` are SpacetimeDB reducers that return
// `Result<(), String>` — i.e. the client never sees the new row's id directly.
// Instead, we identify our own rows by `(submitter == myIdentity AND
// created_at >= callTimestampMicros)` and observe them via subscription.
//
// To eliminate the race where the worker could set our row's status before
// our subscription is live, we follow the **subscribe-first** pattern: open
// the subscription, then call the reducer in the `onApplied` callback so the
// reducer-side row insert never lands before we are listening.
//
// TODO(Phase 4 modularization): once the legacy HTTP path is removed, fold
// these helpers into per-step components.

import type { DbConnection } from "@sastaspace/stdb-bindings";
import type { Identity, Timestamp } from "spacetimedb";

export type Track = {
  name: string;
  type: string;
  length: number;
  desc: string;
  tempo: string;
  instruments: string;
  mood: string;
};

export type PlanResult =
  | { kind: "done"; tracks: Track[]; planRequestId: bigint }
  | { kind: "failed"; error: string };

export type GenerateResult =
  | { kind: "done"; zipUrl: string; jobId: bigint }
  | { kind: "failed"; error: string };

const PLAN_TIMEOUT_MS = 60_000;
const GENERATE_TIMEOUT_MS = 5 * 60_000; // MusicGen render is slow

type PlanRow = {
  id: bigint;
  submitter: Identity;
  description: string;
  count: number;
  status: string;
  tracksJson: string | undefined;
  error: string | undefined;
  createdAt: Timestamp;
  completedAt: Timestamp | undefined;
};

type JobRow = {
  id: bigint;
  submitter: Identity;
  planRequestId: bigint | undefined;
  tracksJson: string;
  status: string;
  zipUrl: string | undefined;
  error: string | undefined;
  createdAt: Timestamp;
  completedAt: Timestamp | undefined;
};

/**
 * Submit a plan request and await its result.
 *
 * Pattern (race-free):
 *   1. capture `tCall = Date.now() * 1000` micros
 *   2. subscribe to `plan_request WHERE submitter = me`
 *   3. on subscription-applied, call `request_plan` reducer
 *   4. resolve when our row (filtered by createdAt >= tCall) flips to
 *      done or failed
 */
export function submitPlan(
  conn: DbConnection,
  identityHex: string,
  description: string,
  count: number,
): Promise<PlanResult> {
  return new Promise((resolve, reject) => {
    const tCall = BigInt(Date.now()) * 1000n;
    let settled = false;
    let unsub: (() => void) | null = null;
    let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

    const finish = (r: PlanResult) => {
      if (settled) return;
      settled = true;
      if (timeoutHandle) clearTimeout(timeoutHandle);
      if (unsub) unsub();
      resolve(r);
    };

    timeoutHandle = setTimeout(() => {
      if (!settled) {
        settled = true;
        if (unsub) unsub();
        reject(new Error("plan timeout"));
      }
    }, PLAN_TIMEOUT_MS);

    const checkRow = (row: PlanRow) => {
      if (row.submitter.toHexString() !== identityHex) return;
      if (row.createdAt.microsSinceUnixEpoch < tCall) return;
      if (row.status === "done") {
        try {
          const parsed = JSON.parse(row.tracksJson ?? "[]") as Track[];
          finish({ kind: "done", tracks: parsed, planRequestId: row.id });
        } catch (e) {
          finish({ kind: "failed", error: `tracks_json parse: ${String(e)}` });
        }
      } else if (row.status === "failed") {
        finish({ kind: "failed", error: row.error ?? "unknown error" });
      }
    };

    // Step 2: subscribe (filter is best-effort on submitter; createdAt
    // gating is enforced client-side in checkRow).
    const handle = conn
      .subscriptionBuilder()
      .onApplied(() => {
        // Step 3: only NOW call the reducer — subscription is live.
        try {
          // Returns Promise<void> per the SDK; the row that lands is what
          // the subscription will surface.
          void conn.reducers.requestPlan({ description, count });
        } catch (e) {
          finish({ kind: "failed", error: `requestPlan threw: ${String(e)}` });
        }
      })
      .onError((_ctx) => {
        finish({ kind: "failed", error: `subscription error` });
      })
      .subscribe([
        `SELECT * FROM plan_request WHERE submitter = X'${identityHex}'`,
      ]);

    const planTable = conn.db.plan_request;
    const onInsertCb = (_ctx: unknown, row: PlanRow) => checkRow(row);
    const onUpdateCb = (_ctx: unknown, _old: PlanRow, row: PlanRow) =>
      checkRow(row);
    // Cast to satisfy the typed callback signatures — the runtime accepts
    // any function with the right arity.
    planTable.onInsert(onInsertCb as Parameters<typeof planTable.onInsert>[0]);
    planTable.onUpdate(
      onUpdateCb as Parameters<typeof planTable.onUpdate>[0],
    );

    unsub = () => {
      try {
        planTable.removeOnInsert(
          onInsertCb as Parameters<typeof planTable.removeOnInsert>[0],
        );
      } catch {
        /* ignore */
      }
      try {
        planTable.removeOnUpdate(
          onUpdateCb as Parameters<typeof planTable.removeOnUpdate>[0],
        );
      } catch {
        /* ignore */
      }
      try {
        handle.unsubscribe();
      } catch {
        /* ignore */
      }
    };

    // Pick up any leftover row that already matches our filter (e.g. from a
    // previous reload). The createdAt gate in checkRow keeps us from
    // confusing it with the new request.
    for (const row of planTable.iter() as IterableIterator<PlanRow>) {
      if (row.submitter.toHexString() === identityHex && row.status !== "pending") {
        checkRow(row);
        if (settled) break;
      }
    }
  });
}

/**
 * Submit a generate job and await its zip url. Same subscribe-first pattern.
 */
export function submitGenerate(
  conn: DbConnection,
  identityHex: string,
  planRequestId: bigint | null,
  editedTracks: Track[],
): Promise<GenerateResult> {
  return new Promise((resolve, reject) => {
    const tCall = BigInt(Date.now()) * 1000n;
    let settled = false;
    let unsub: (() => void) | null = null;
    let timeoutHandle: ReturnType<typeof setTimeout> | null = null;

    const finish = (r: GenerateResult) => {
      if (settled) return;
      settled = true;
      if (timeoutHandle) clearTimeout(timeoutHandle);
      if (unsub) unsub();
      resolve(r);
    };

    timeoutHandle = setTimeout(() => {
      if (!settled) {
        settled = true;
        if (unsub) unsub();
        reject(new Error("generate timeout"));
      }
    }, GENERATE_TIMEOUT_MS);

    const checkRow = (row: JobRow) => {
      if (row.submitter.toHexString() !== identityHex) return;
      if (row.createdAt.microsSinceUnixEpoch < tCall) return;
      if (row.status === "done" && row.zipUrl) {
        finish({ kind: "done", zipUrl: row.zipUrl, jobId: row.id });
      } else if (row.status === "failed") {
        finish({ kind: "failed", error: row.error ?? "unknown error" });
      }
    };

    const tracksJson = JSON.stringify(editedTracks);

    const handle = conn
      .subscriptionBuilder()
      .onApplied(() => {
        try {
          void conn.reducers.requestGenerate({
            planRequestId: planRequestId ?? undefined,
            tracksJson,
          });
        } catch (e) {
          finish({
            kind: "failed",
            error: `requestGenerate threw: ${String(e)}`,
          });
        }
      })
      .onError((_ctx) => {
        finish({ kind: "failed", error: `subscription error` });
      })
      .subscribe([
        `SELECT * FROM generate_job WHERE submitter = X'${identityHex}'`,
      ]);

    const jobTable = conn.db.generate_job;
    const onInsertCb = (_ctx: unknown, row: JobRow) => checkRow(row);
    const onUpdateCb = (_ctx: unknown, _old: JobRow, row: JobRow) =>
      checkRow(row);
    jobTable.onInsert(onInsertCb as Parameters<typeof jobTable.onInsert>[0]);
    jobTable.onUpdate(onUpdateCb as Parameters<typeof jobTable.onUpdate>[0]);

    unsub = () => {
      try {
        jobTable.removeOnInsert(
          onInsertCb as Parameters<typeof jobTable.removeOnInsert>[0],
        );
      } catch {
        /* ignore */
      }
      try {
        jobTable.removeOnUpdate(
          onUpdateCb as Parameters<typeof jobTable.removeOnUpdate>[0],
        );
      } catch {
        /* ignore */
      }
      try {
        handle.unsubscribe();
      } catch {
        /* ignore */
      }
    };

    for (const row of jobTable.iter() as IterableIterator<JobRow>) {
      if (row.submitter.toHexString() === identityHex && row.status !== "pending") {
        checkRow(row);
        if (settled) break;
      }
    }
  });
}

/**
 * Stream the zip from a known URL to a Blob and trigger a browser download.
 * Mirrors `triggerDownload` in Deck.tsx but starts from a URL instead of a
 * Blob so we can use the worker-produced zip directly.
 */
export async function downloadZipFromUrl(
  zipUrl: string,
  filename = "deck.zip",
): Promise<void> {
  const r = await fetch(zipUrl);
  if (!r.ok) throw new Error(`zip fetch ${r.status}`);
  const blob = await r.blob();
  const objUrl = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = objUrl;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(objUrl), 1000);
}
