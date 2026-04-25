// Tiny SpacetimeDB SQL helper for tests that need to verify state without
// driving the UI (e.g. "did the moderator approve this comment?").

import type { APIRequestContext } from "@playwright/test";
import { STDB_DATABASE, STDB_REST } from "./urls.js";

export async function sql(
  request: APIRequestContext,
  query: string,
  ownerToken?: string,
): Promise<unknown[][]> {
  const headers: Record<string, string> = { "Content-Type": "text/plain" };
  if (ownerToken) headers.Authorization = `Bearer ${ownerToken}`;
  const r = await request.post(`${STDB_REST}/v1/database/${STDB_DATABASE}/sql`, {
    headers,
    data: query,
  });
  if (r.status() >= 400) {
    throw new Error(`stdb SQL failed: HTTP ${r.status()} ${await r.text()}`);
  }
  const payload = (await r.json()) as Array<{ rows?: unknown[][] }>;
  if (!Array.isArray(payload) || payload.length === 0) return [];
  return payload[0].rows ?? [];
}

/** Polls until the predicate returns truthy or `timeoutMs` elapses. */
export async function pollUntil<T>(
  fn: () => Promise<T | null | undefined | false>,
  opts: { timeoutMs?: number; intervalMs?: number; what?: string } = {},
): Promise<T> {
  const timeout = opts.timeoutMs ?? 15_000;
  const interval = opts.intervalMs ?? 500;
  const what = opts.what ?? "condition";
  const start = Date.now();
  let last: unknown = null;
  while (Date.now() - start < timeout) {
    last = await fn();
    if (last) return last as T;
    await new Promise((r) => setTimeout(r, interval));
  }
  throw new Error(`pollUntil timed out after ${timeout}ms waiting for ${what}; last=${String(last)}`);
}
