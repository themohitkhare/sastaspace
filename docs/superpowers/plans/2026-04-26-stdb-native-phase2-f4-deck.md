# Phase 2 F4 — Deck Frontend Rewire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (run as one of 4 parallel Phase 2 workstream subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `apps/landing/src/app/lab/deck/Deck.tsx` HTTP calls (`fetch('/plan')`, `fetch('/generate')` against `services/deck`) with SpacetimeDB reducer calls (`request_plan`, `request_generate`) plus subscriptions on `plan_request` and `generate_job`. Both code paths coexist behind `NEXT_PUBLIC_USE_STDB_DECK`. The visual UI is unchanged — this is a wiring rewire only.

**Architecture:** A new `useDeckStdb` hook owns the STDB connection. It mints a per-browser anonymous identity once and persists the JWT in `localStorage` under `sastaspace.deck.anon.v1` so a page reload mid-render still observes the in-flight job. Plan / generate actions become two helpers (`submitPlan`, `submitGenerate`) that **subscribe first, then call the reducer**, then resolve when their own row flips to `done` or `failed`. Existing `fetchPlan`/`fetchGenerate`/`stubZipBlob` paths stay verbatim, gated by the env flag, so cutover is a one-line flip and rollback is the same flip in reverse.

**Tech Stack:** TypeScript (React hook + `@sastaspace/stdb-bindings` generated `DbConnection`/`reducers`/`tables`), Next.js (env flag), Playwright (E2E across both flag states).

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` § "Per-app frontend changes / apps/landing/" + open Q7 (zip URL shape — already resolved by W3 to `https://deck.sastaspace.com/<job_id>.zip`).

**Master plan:** `docs/superpowers/plans/2026-04-26-stdb-native-master.md`

**Upstream W3 reducer signatures (confirmed against `packages/stdb-bindings/src/generated/`):**
- `request_plan(description: string, count: u32) → Result<(), String>` — **no return value**. Client observes its own row by subscribing to `plan_request WHERE submitter = <my_identity>` and watching for the new auto-inc id.
- `request_generate(plan_request_id: Option<u64>, tracks_json: string) → Result<(), String>` — same pattern. (Note: the W3 Rust source declares these `Result<u64, String>`, but the regenerated bindings expose them as `(): void` — SpacetimeDB reducers do not surface return values to clients, only via subscription. The W3 plan's "returns id" wording is inaccurate; treat the canonical contract as "fire reducer, observe row.")
- `plan_request` columns: `id`, `submitter`, `description`, `count`, `status` ("pending"|"done"|"failed"), `tracks_json` (`Option<string>`), `error` (`Option<string>`), `created_at`, `completed_at`.
- `generate_job` columns: `id`, `submitter`, `plan_request_id` (`Option<u64>`), `tracks_json`, `status` ("pending"|"done"|"failed"), `zip_url` (`Option<string>`), `error` (`Option<string>`), `created_at`, `completed_at`.

**Coordination:** Touches only `apps/landing/`, `packages/stdb-bindings/` (consumer-only — no regen), and `tests/e2e/specs/deck.spec.ts` (new). No conflict surface with F1/F2/F3. The W3 worker (`workers/src/agents/deck-agent.ts`) must be running with `WORKER_DECK_AGENT_ENABLED=true` for the rewired path to flip rows past `pending` — F4 acceptance assumes W3 is healthy on the dev compose.

**Out of scope:** Modularization of the 1,421-line `Deck.tsx`. Audit M1 flagged it for splitting but F4 is **additive only** — the new code path is gated, the old path is untouched. See "Risks" below.

---

## Task 1: Add the `useDeckStdb` connection + identity hook

**Files:**
- Create: `apps/landing/src/app/lab/deck/useDeckStdb.ts`

The lab page is public — no Google/magic-link sign-in. STDB still requires an identity, so we mint one anonymously via the SDK's built-in identity bootstrap and persist the JWT in `localStorage` so the same browser keeps the same identity across reloads. This lets a user reload mid-render and still see "their" `generate_job` row.

- [ ] **Step 1: Create the hook**

```typescript
// apps/landing/src/app/lab/deck/useDeckStdb.ts
"use client";

import { useEffect, useRef, useState } from "react";
import { DbConnection, type EventContext } from "@sastaspace/stdb-bindings";

const STDB_URI =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
const STDB_MODULE =
  process.env.NEXT_PUBLIC_SASTASPACE_MODULE ?? "sastaspace";

const TOKEN_KEY = "sastaspace.deck.anon.v1";

function loadToken(): string | undefined {
  if (typeof window === "undefined") return undefined;
  return window.localStorage.getItem(TOKEN_KEY) ?? undefined;
}

function saveToken(token: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(TOKEN_KEY, token);
}

export type DeckStdb = {
  conn: DbConnection;
  /** Hex identity of the connected client; stable across reloads in this browser. */
  identityHex: string;
};

/**
 * Connects to the sastaspace module with an anonymous identity, persisted
 * across reloads via `localStorage[TOKEN_KEY]`. Returns null while connecting.
 * Tears down on unmount.
 */
export function useDeckStdb(enabled: boolean): DeckStdb | null {
  const [state, setState] = useState<DeckStdb | null>(null);
  // StrictMode in dev double-invokes effects; guard against double-connect.
  const builtRef = useRef(false);

  useEffect(() => {
    if (!enabled) return;
    if (builtRef.current) return;
    builtRef.current = true;

    let cancelled = false;
    const builder = DbConnection.builder()
      .withUri(STDB_URI)
      .withDatabaseName(STDB_MODULE)
      .onConnect((ctx: EventContext, identity, token) => {
        if (cancelled) return;
        if (token) saveToken(token);
        setState({ conn: ctx.db ? (ctx as unknown as { db: DbConnection }).db ?? (ctx as unknown as DbConnection) : (ctx as unknown as DbConnection), identityHex: identity.toHexString() });
      })
      .onConnectError((_ctx, err) => {
        console.warn("[deck] stdb connect error:", err);
      });

    const existing = loadToken();
    const conn = (existing ? builder.withToken(existing) : builder).build();

    return () => {
      cancelled = true;
      try {
        conn.disconnect();
      } catch {
        /* ignore */
      }
    };
  }, [enabled]);

  return state;
}
```

(The exact shape returned by `onConnect` — whether the connection is on `ctx.db`, on `ctx` itself, or returned from `.build()` — depends on the SDK version. Inspect the typed `EventContext` in `packages/stdb-bindings/src/generated/index.ts` and the existing wiring in `apps/typewars/src/lib/spacetime.ts` + `apps/admin/src/hooks/useStdb.ts` to confirm; the cast above is a fallback if the type isn't directly exposed. Adapt the body to follow whichever access pattern the typewars hook already uses.)

- [ ] **Step 2: Lint + typecheck**

```bash
cd apps/landing && pnpm typecheck && pnpm lint
```

Expected: clean. If the SDK access cast is wrong, the typecheck will tell you exactly what to use.

- [ ] **Step 3: Commit**

```bash
git add apps/landing/src/app/lab/deck/useDeckStdb.ts
git commit -m "$(cat <<'EOF'
feat(landing/deck): useDeckStdb hook — anonymous persisted identity

Phase 2 F4 step 1. Adds the per-browser STDB connection helper for the
deck lab page. Mints an anonymous identity on first load, persists the
JWT in localStorage under sastaspace.deck.anon.v1 so reloads keep the
same identity (lets a user reload mid-render and still see their job).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add the plan + generate flow helpers (subscribe-then-call pattern)

**Files:**
- Create: `apps/landing/src/app/lab/deck/deckStdbFlows.ts`

Two functions, both implementing the **subscribe-first** pattern to eliminate the race where the row could land before our subscription is live. The W3 reducer signatures don't return ids, so we identify our own rows by `(submitter == myIdentity AND created_at >= callTimestampMicros)`.

- [ ] **Step 1: Create the flow helpers**

```typescript
// apps/landing/src/app/lab/deck/deckStdbFlows.ts
"use client";

import { reducers, tables, type DbConnection, type SubscriptionEventContext } from "@sastaspace/stdb-bindings";

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

/**
 * Submit a plan request and await its result.
 *
 * Pattern (race-free):
 *   1. capture `tCall = Date.now() * 1000` micros
 *   2. subscribe to `plan_request WHERE submitter = me AND created_at >= tCall`
 *   3. on subscription-applied, call `request_plan` reducer
 *   4. resolve when our row (the only one matching the filter) flips to
 *      done or failed
 *
 * Step (3) gates the reducer call on the subscription being live so the
 * insert never lands before we're listening.
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

    const checkRow = (row: {
      submitter: { toHexString: () => string };
      createdAt: { toMicrosSinceUnixEpoch: () => bigint };
      status: string;
      tracksJson: string | null;
      error: string | null;
      id: bigint;
    }) => {
      if (row.submitter.toHexString() !== identityHex) return;
      if (row.createdAt.toMicrosSinceUnixEpoch() < tCall) return;
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

    // Step 2: subscribe
    const handle = conn
      .subscriptionBuilder()
      .onApplied((_ctx: SubscriptionEventContext) => {
        // Step 3: only NOW call the reducer — subscription is live.
        try {
          reducers.requestPlan(conn, description, count);
        } catch (e) {
          finish({ kind: "failed", error: `requestPlan threw: ${String(e)}` });
        }
      })
      .onError((_ctx, err) => {
        finish({ kind: "failed", error: `subscription error: ${String(err)}` });
      })
      .subscribe([
        `SELECT * FROM plan_request WHERE submitter = X'${identityHex}'`,
      ]);

    // Wire row-event callbacks. The exact accessor name (camel vs snake) is
    // what the regenerated bindings expose — confirm against
    // packages/stdb-bindings/src/generated/index.ts before shipping.
    const planTable = tables.planRequest(conn);
    const offInsert = planTable.onInsert((_ctx, row) => checkRow(row));
    const offUpdate = planTable.onUpdate((_ctx, _old, row) => checkRow(row));

    unsub = () => {
      try { offInsert(); } catch { /* ignore */ }
      try { offUpdate(); } catch { /* ignore */ }
      try { handle.unsubscribe(); } catch { /* ignore */ }
    };

    // If a leftover row from a previous reload already matches our filter
    // (page reload mid-render), pick it up immediately on first iter().
    for (const row of planTable.iter()) {
      if (row.submitter.toHexString() === identityHex && row.status !== "pending") {
        // We can't distinguish "ours from this call" from "leftover" without
        // tCall — but tCall pre-dates this row, so the createdAt check below
        // still gates correctly.
        checkRow(row);
        if (settled) break;
      }
    }
  });
}

/**
 * Submit a generate job and await zip url. Same subscribe-first pattern.
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

    const checkRow = (row: {
      submitter: { toHexString: () => string };
      createdAt: { toMicrosSinceUnixEpoch: () => bigint };
      status: string;
      zipUrl: string | null;
      error: string | null;
      id: bigint;
    }) => {
      if (row.submitter.toHexString() !== identityHex) return;
      if (row.createdAt.toMicrosSinceUnixEpoch() < tCall) return;
      if (row.status === "done" && row.zipUrl) {
        finish({ kind: "done", zipUrl: row.zipUrl, jobId: row.id });
      } else if (row.status === "failed") {
        finish({ kind: "failed", error: row.error ?? "unknown error" });
      }
    };

    const tracksJson = JSON.stringify(editedTracks);

    const handle = conn
      .subscriptionBuilder()
      .onApplied((_ctx) => {
        try {
          reducers.requestGenerate(conn, planRequestId, tracksJson);
        } catch (e) {
          finish({ kind: "failed", error: `requestGenerate threw: ${String(e)}` });
        }
      })
      .onError((_ctx, err) => {
        finish({ kind: "failed", error: `subscription error: ${String(err)}` });
      })
      .subscribe([
        `SELECT * FROM generate_job WHERE submitter = X'${identityHex}'`,
      ]);

    const jobTable = tables.generateJob(conn);
    const offInsert = jobTable.onInsert((_ctx, row) => checkRow(row));
    const offUpdate = jobTable.onUpdate((_ctx, _old, row) => checkRow(row));

    unsub = () => {
      try { offInsert(); } catch { /* ignore */ }
      try { offUpdate(); } catch { /* ignore */ }
      try { handle.unsubscribe(); } catch { /* ignore */ }
    };

    for (const row of jobTable.iter()) {
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
export async function downloadZipFromUrl(zipUrl: string, filename = "deck.zip"): Promise<void> {
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
```

**Important caveats verifying against the SDK before this compiles:**

1. The exact reducer-call shape — `reducers.requestPlan(conn, …)` vs `conn.reducers.requestPlan(…)` vs `conn.callReducer("request_plan", …)` — depends on the codegen layout. Read `packages/stdb-bindings/src/generated/index.ts` (the `reducers = __convertToAccessorMap(...)` export) to see the actual call pattern. Adapt the two `reducers.requestPlan(...)` / `reducers.requestGenerate(...)` lines accordingly.
2. Same for `tables.planRequest(conn)` — the `tables` export is `__makeQueryBuilder(...)`. Inspect the runtime shape (e.g. `pnpm exec tsx -e "import { tables } from '@sastaspace/stdb-bindings'; console.log(Object.keys(tables));"`) and adapt accessors.
3. `Identity.toHexString()` is the standard SDK method; if it's `Identity.toHex()` or `.toString("hex")`, swap.
4. The SQL filter uses `X'<hex>'` for an Identity literal; SpacetimeDB's SQL dialect supports this. If subscription-applied rejects with a parse error, confirm the literal syntax in the SDK's docs and adjust (the alternative is to subscribe to the unfiltered table and filter client-side — slower but always works).

- [ ] **Step 2: Typecheck**

```bash
cd apps/landing && pnpm typecheck
```

Expected: clean. Any drift between the assumed SDK shape and the real generated bindings shows up here as the place to fix the casts above.

- [ ] **Step 3: Commit**

```bash
git add apps/landing/src/app/lab/deck/deckStdbFlows.ts
git commit -m "$(cat <<'EOF'
feat(landing/deck): submitPlan + submitGenerate STDB flow helpers

Phase 2 F4 step 2. Implements the subscribe-first reducer-call pattern
for the deck lab page: subscribe to plan_request (resp. generate_job)
filtered to my identity, then call the reducer in onApplied so the row
insert never races the subscription. Resolves when the row flips to
done/failed. Includes downloadZipFromUrl helper for the result step.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Wire the flag-gated STDB code path into `Deck.tsx`

**Files:**
- Modify: `apps/landing/src/app/lab/deck/Deck.tsx`

The existing `onPlan` callback (Deck.tsx:89–122) and `onDownload` callback (Deck.tsx:811–823) both branch on `API_URL`. We add a parallel branch for `useStdb` that runs **before** the `API_URL` check so the flag flips behavior cleanly. The visual states (`phase`, `planProgress`, `zipLabel`) are unchanged — the new branch sets the same state, just from STDB rather than HTTP.

- [ ] **Step 1: Add the env-flag constant near `API_URL`**

In `Deck.tsx`, just below the existing `const API_URL = process.env.NEXT_PUBLIC_DECK_API_URL;` (line 10), add:

```typescript
// When true, route /plan and /generate through SpacetimeDB reducers
// (Phase 2 F4) instead of the deprecated services/deck HTTP API. Both
// paths coexist until Phase 3 cutover; default false until cutover.
const USE_STDB = process.env.NEXT_PUBLIC_USE_STDB_DECK === "true";
```

- [ ] **Step 2: Mount `useDeckStdb` inside the `Deck` component**

Inside the `Deck` function (immediately after the `useState` block around line 81), add:

```typescript
import { useDeckStdb } from "./useDeckStdb";
import { submitPlan, submitGenerate, downloadZipFromUrl, type Track as StdbTrack } from "./deckStdbFlows";

// ... inside Deck() ...
const stdb = useDeckStdb(USE_STDB);
// Tracks the plan_request id returned from the STDB plan flow so the
// subsequent generate flow can cite it (lets the reducer enforce
// "only the submitter may generate from their own plan").
const [stdbPlanId, setStdbPlanId] = useState<bigint | null>(null);
```

(Adjust the imports — Deck.tsx already imports React hooks at the top.)

- [ ] **Step 3: Replace `onPlan` body with a flag-aware version**

Modify the `onPlan` callback (line 89). Keep the existing `API_URL`/local-fallback branch verbatim; add a new branch that runs first when `USE_STDB && stdb`:

```typescript
const onPlan = useCallback(() => {
  if (!canPlan) return;
  setPhase("planning");
  setPlanProgress(0);
  const start = performance.now();
  const minDur = 1700;

  // ────────── F4: STDB path ──────────
  if (USE_STDB && stdb) {
    let resolvedTracks: Track[] | null = null;
    let resolvedPlanId: bigint | null = null;
    let apiSettled = false;
    void submitPlan(stdb.conn, stdb.identityHex, trimmed, desiredCount)
      .then((res) => {
        if (res.kind === "done") {
          resolvedTracks = res.tracks.map((t) => ({
            id: nextId(),
            ...t,
          }));
          resolvedPlanId = res.planRequestId;
        } else {
          console.warn("[deck] stdb plan failed, using local draft:", res.error);
        }
      })
      .catch((err) => {
        console.warn("[deck] stdb plan threw, using local draft:", err);
      })
      .finally(() => {
        apiSettled = true;
      });
    const id = window.setInterval(() => {
      const r = Math.min((performance.now() - start) / minDur, 1);
      setPlanProgress(r);
      if (r >= 1 && apiSettled) {
        window.clearInterval(id);
        setPlan(resolvedTracks ?? draftPlan(trimmed, desiredCount));
        setStdbPlanId(resolvedPlanId);
        setPhase("plan");
        setOpenId(null);
      }
    }, 60);
    return;
  }

  // ────────── legacy: HTTP path ──────────
  let resolvedTracks: Track[] | null = null;
  let apiSettled = !API_URL;
  if (API_URL) {
    void fetchPlan(API_URL, trimmed, desiredCount)
      .then((tracks) => { resolvedTracks = tracks; })
      .catch((err) => { console.warn("[deck] /plan failed, using local draft:", err); })
      .finally(() => { apiSettled = true; });
  }
  const id = window.setInterval(() => {
    const r = Math.min((performance.now() - start) / minDur, 1);
    setPlanProgress(r);
    if (r >= 1 && apiSettled) {
      window.clearInterval(id);
      setPlan(resolvedTracks ?? draftPlan(trimmed, desiredCount));
      setPhase("plan");
      setOpenId(null);
    }
  }, 60);
}, [canPlan, trimmed, desiredCount, stdb]);
```

- [ ] **Step 4: Replace `onDownload` (in the `Step3Results` component) with a flag-aware version**

`onDownload` lives at line 811. The current implementation always calls `fetchGenerate` (or stub). Replace with:

```typescript
const onDownload = useCallback(async () => {
  setZipLabel("building zip…");
  try {
    if (USE_STDB && stdb) {
      // Strip client-side ids before sending to the reducer.
      const tracks: StdbTrack[] = plan.map(({ id, ...rest }) => { void id; return rest; });
      const res = await submitGenerate(stdb.conn, stdb.identityHex, stdbPlanId, tracks);
      if (res.kind === "done") {
        await downloadZipFromUrl(res.zipUrl, "deck.zip");
        setZipLabel("downloaded ✓");
      } else {
        console.warn("[deck] stdb generate failed:", res.error);
        setZipLabel("download failed — retry");
      }
      return;
    }
    const blob = API_URL
      ? await fetchGenerate(API_URL, prompt, plan)
      : await stubZipBlob();
    triggerDownload(blob, "deck.zip");
    setZipLabel("downloaded ✓");
  } catch (err) {
    console.warn("[deck] /generate failed:", err);
    setZipLabel("download failed — retry");
  }
}, [plan, prompt, stdb, stdbPlanId]);
```

`Step3Results` doesn't currently take `stdb`/`stdbPlanId` as props. Plumb them down: change the `Step3Results` invocation site to pass `stdb` and `stdbPlanId`, and update its `props` type to accept them as `DeckStdb | null` and `bigint | null` respectively. (Alternative: lift `useDeckStdb` into a React Context for the lab page; the prop-drilling is mechanical and small enough that a context isn't required for one consumer.)

- [ ] **Step 5: Verify `phase` transitions still match the legacy UX**

Manually walk through the four UI states (the spec's required handling):

- **drafting plan…** — `phase === "planning"` while `submitPlan` is in flight; the existing `Step1Idle`/transition CSS already handles this.
- **render queued / rendering…** — `zipLabel === "building zip…"` while `submitGenerate` is in flight; `Step3Results` already renders this.
- **ready** — `zipLabel === "downloaded ✓"`; existing.
- **failed** — `zipLabel === "download failed — retry"`; existing.

Throughout: real-time, no polling — STDB subscriptions push updates. The `submitPlan`/`submitGenerate` promises resolve as soon as the worker calls `set_plan` / `set_generate_done`. ✅

- [ ] **Step 6: Typecheck + lint + build**

```bash
cd apps/landing && pnpm typecheck && pnpm lint && pnpm build
```

Expected: clean. The build also catches any SSR-vs-client boundary issues (`useDeckStdb` is `"use client"` and only mounted inside the already-client `Deck` component, so SSR shouldn't trip).

- [ ] **Step 7: Commit**

```bash
git add apps/landing/src/app/lab/deck/Deck.tsx
git commit -m "$(cat <<'EOF'
feat(landing/deck): flag-gated STDB code path in Deck.tsx (additive)

Phase 2 F4 step 3. Wires the STDB plan + generate flow into Deck.tsx
behind NEXT_PUBLIC_USE_STDB_DECK. Both code paths coexist; the legacy
HTTP path (services/deck) is untouched and remains the default until
Phase 3 cutover. Visual states (phase, planProgress, zipLabel) are
unchanged — only the data source differs.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Add the env flag to local + prod compose

**Files:**
- Modify: `infra/docker-compose.yml` — landing service env block

The flag is a **build-time** env in Next.js (`NEXT_PUBLIC_*`), so it bakes into the static export at `pnpm build`. Setting it on the running landing container is a no-op; it has to be set when the apps build. For dev, add it to the build args / `.env.local` documentation; for compose, add it as an arg the build stage consumes.

- [ ] **Step 1: Document the dev-time flag**

Append to `apps/landing/README.md` (or create one if absent), under an "Environment" heading:

```markdown
## Environment

- `NEXT_PUBLIC_DECK_API_URL` — deck service URL (legacy; will be removed in Phase 4)
- `NEXT_PUBLIC_USE_STDB_DECK` — set to `true` to route /lab/deck through SpacetimeDB
  reducers instead of the legacy HTTP service (Phase 2 F4 cutover gate)
- `NEXT_PUBLIC_STDB_URI` — defaults to `wss://stdb.sastaspace.com`
- `NEXT_PUBLIC_SASTASPACE_MODULE` — defaults to `sastaspace`
```

- [ ] **Step 2: Wire the flag into the landing build stage in compose**

In `infra/docker-compose.yml`, find the `landing` service block. Under its `build:` stanza, add:

```yaml
build:
  context: ../
  dockerfile: apps/landing/Dockerfile
  args:
    NEXT_PUBLIC_USE_STDB_DECK: "false"   # flip to "true" at Phase 3 cutover
    NEXT_PUBLIC_STDB_URI: "wss://stdb.sastaspace.com"
    NEXT_PUBLIC_SASTASPACE_MODULE: "sastaspace"
```

If `apps/landing/Dockerfile` doesn't already declare these as `ARG` and forward them to `ENV` before `pnpm build`, add:

```dockerfile
ARG NEXT_PUBLIC_USE_STDB_DECK=false
ARG NEXT_PUBLIC_STDB_URI
ARG NEXT_PUBLIC_SASTASPACE_MODULE
ENV NEXT_PUBLIC_USE_STDB_DECK=${NEXT_PUBLIC_USE_STDB_DECK} \
    NEXT_PUBLIC_STDB_URI=${NEXT_PUBLIC_STDB_URI} \
    NEXT_PUBLIC_SASTASPACE_MODULE=${NEXT_PUBLIC_SASTASPACE_MODULE}
```

- [ ] **Step 3: Smoke-build both flag values**

```bash
NEXT_PUBLIC_USE_STDB_DECK=false pnpm --filter '@sastaspace/landing' build
NEXT_PUBLIC_USE_STDB_DECK=true  pnpm --filter '@sastaspace/landing' build
```

Expected: both succeed. Inspect `apps/landing/.next/server/chunks/` (or wherever the static export lands) to confirm the flag baked in (`grep -r "USE_STDB_DECK" .next/` should show the value the build saw — Next.js inlines `NEXT_PUBLIC_*` constants).

- [ ] **Step 4: Commit**

```bash
git add infra/docker-compose.yml apps/landing/Dockerfile apps/landing/README.md
git commit -m "$(cat <<'EOF'
chore(infra/landing): NEXT_PUBLIC_USE_STDB_DECK build arg + docs

Phase 2 F4 step 4. Plumbs the flag from compose build args through the
landing Dockerfile so the build stage bakes the right path into the
static export. Default false until Phase 3 cutover.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Manual smoke test — both flag states

**Files:** none (verification only)

- [ ] **Step 1: Bring up the dependent stack**

```bash
docker compose up -d spacetime ollama localai workers landing
docker compose logs -f workers   # watch for "deck-agent started"
```

If `workers` doesn't have `WORKER_DECK_AGENT_ENABLED=true`, set it in the compose env or pass it inline:

```bash
WORKER_DECK_AGENT_ENABLED=true docker compose up -d workers
```

- [ ] **Step 2: Legacy path (flag off) — confirm no regression**

```bash
NEXT_PUBLIC_USE_STDB_DECK=false pnpm --filter '@sastaspace/landing' dev
# in browser, open http://localhost:3000/lab/deck
# enter a brief, hit "draft plan", confirm the existing flow still works
# (either via deck service if NEXT_PUBLIC_DECK_API_URL is set, or via
# local fallback)
# click download, confirm a zip downloads (real or stub)
```

Expected: identical UX to pre-F4. No console warnings about `useDeckStdb`.

- [ ] **Step 3: STDB path (flag on) — happy path**

```bash
NEXT_PUBLIC_USE_STDB_DECK=true \
NEXT_PUBLIC_STDB_URI=ws://localhost:3100 \
NEXT_PUBLIC_SASTASPACE_MODULE=sastaspace \
  pnpm --filter '@sastaspace/landing' dev
# browser → http://localhost:3000/lab/deck
# enter "A meditation app for stressed professionals", count=3
# click "draft plan"
# expect: planning state for ~2-30s (depends on Ollama latency), then
#   plan view appears with 3 tracks, mood=calm
# inspect the row in another terminal:
spacetime sql sastaspace \
  "SELECT id, status, length(tracks_json) FROM plan_request ORDER BY id DESC LIMIT 1"
# click "generate" / "download .zip"
# expect: "building zip…" → eventual "downloaded ✓" with a real zip in
#   ~Downloads
spacetime sql sastaspace \
  "SELECT id, status, zip_url FROM generate_job ORDER BY id DESC LIMIT 1"
```

Expected: both rows flip from `pending` to `done` within their respective timeouts; the downloaded zip contains a `README.txt` plus per-track `.wav` files.

- [ ] **Step 4: STDB path — reload mid-render survives**

```bash
# repeat step 3, but as soon as "generating" shows, hard-refresh the page
# (Cmd+Shift+R). Re-open /lab/deck.
# expect: the page is back at idle (UI state was lost), but the
# generate_job row in STDB still completes — confirm via:
spacetime sql sastaspace "SELECT id, status, zip_url FROM generate_job ORDER BY id DESC LIMIT 1"
# i.e. the BACKEND survives the reload; the FRONTEND state does not.
# This is the F4 contract — full UI-state-survival is out of scope (would
# need to surface a "in-flight job" banner from useDeckStdb).
```

Document this limitation — full reload-survival is a future enhancement, see "Risks" below.

- [ ] **Step 5: STDB path — failure state**

```bash
docker compose stop workers
# repeat step 3; expect: planning state hangs until PLAN_TIMEOUT_MS (60s),
# then the local-draft fallback kicks in (resolvedTracks is null →
# draftPlan() runs). The legacy HTTP fallback behaviour is preserved.
docker compose start workers
```

Expected: timeout doesn't crash the page; it falls through to the local draft just like the legacy path's `catch` does.

---

## Task 6: New E2E spec — `tests/e2e/specs/deck.spec.ts`

**Files:**
- Create: `tests/e2e/specs/deck.spec.ts`

The spec runs in two modes (matrix or two `describe.parallel` blocks): with `NEXT_PUBLIC_USE_STDB_DECK=false` (legacy path) and `=true` (rewired path). Phase 2 acceptance per the master plan: "E2E spec for that app's user-visible flows passes against the rewired path AND against the legacy path."

- [ ] **Step 1: Write the spec**

```typescript
// tests/e2e/specs/deck.spec.ts
import { test, expect } from "@playwright/test";
import path from "node:path";

const LANDING_URL = process.env.E2E_LANDING_URL ?? "http://localhost:3000";
// E2E_DECK_FLOW=stdb runs against the STDB path; anything else runs the legacy.
const FLOW = process.env.E2E_DECK_FLOW ?? "legacy";

test.describe(`/lab/deck (${FLOW})`, () => {
  test("submit brief → plan appears → generate → zip downloads", async ({ page, context }) => {
    test.setTimeout(8 * 60_000); // MusicGen render is slow on first run

    await page.goto(`${LANDING_URL}/lab/deck`);
    await expect(page.getByRole("textbox")).toBeVisible();

    await page.getByRole("textbox").fill(
      "A meditation app for stressed professionals. Calm, slow, soft pads, no percussion.",
    );

    // Step 1 → Step 2 (planning → plan)
    await page.getByRole("button", { name: /draft plan/i }).click();
    // The animation forces a min ~1.7s; allow up to 60s for STDB worker to flip the row.
    await expect(page.getByText(/edit plan|step 2/i)).toBeVisible({ timeout: 60_000 });
    // At least one track row should be visible.
    await expect(page.locator("[class*='track']").first()).toBeVisible();

    // Step 2 → Step 3 (plan → generate / results)
    await page.getByRole("button", { name: /^generate$|continue|approve plan/i }).click();
    await expect(page.getByRole("button", { name: /download \.zip/i })).toBeVisible({ timeout: 30_000 });

    // Click download, intercept the resulting download.
    const downloadPromise = page.waitForEvent("download");
    await page.getByRole("button", { name: /download \.zip/i }).click();
    const download = await downloadPromise;

    // Save and verify it's non-trivial (>100 bytes for legacy stub; >1KB for real zip).
    const dest = path.join(test.info().outputDir, await download.suggestedFilename());
    await download.saveAs(dest);
    const fs = await import("node:fs/promises");
    const stat = await fs.stat(dest);
    if (FLOW === "stdb") {
      expect(stat.size).toBeGreaterThan(1024); // real zip with WAVs
    } else {
      expect(stat.size).toBeGreaterThan(100);  // legacy stub or real zip
    }
  });

  test("very-short brief is rejected before submission", async ({ page }) => {
    await page.goto(`${LANDING_URL}/lab/deck`);
    await page.getByRole("textbox").fill("hi"); // <4 chars
    const btn = page.getByRole("button", { name: /draft plan/i });
    await expect(btn).toBeDisabled();
  });
});
```

(The button labels and selectors above are guesses based on the audit description of Deck.tsx. Inspect the rendered DOM during Step 1 of Task 5 (open devtools, look at the buttons' accessible names) and adjust the regexes if they don't match. Prefer `getByRole`+name regex over CSS selectors so re-styling doesn't break the spec.)

- [ ] **Step 2: Wire the dual-flow run into CI**

Add to `tests/e2e/playwright.config.ts` (or wherever projects are declared) a second project entry that sets `E2E_DECK_FLOW=stdb` and points the `webServer` (or expects an externally-running landing) at a build with `NEXT_PUBLIC_USE_STDB_DECK=true`. If the existing CI matrix is per-app, two new matrix entries (`landing-legacy`, `landing-stdb`) that build with the right flag value before running the spec is the cleanest approach.

If a quick path is preferred (CI matrix work is heavier), at least gate with an env so a developer can run both manually:

```bash
E2E_DECK_FLOW=legacy pnpm test:e2e tests/e2e/specs/deck.spec.ts
E2E_DECK_FLOW=stdb   pnpm test:e2e tests/e2e/specs/deck.spec.ts
```

- [ ] **Step 3: Run the spec**

```bash
# Legacy path (workers off, deck service running)
E2E_DECK_FLOW=legacy pnpm test:e2e tests/e2e/specs/deck.spec.ts

# STDB path (workers on with WORKER_DECK_AGENT_ENABLED=true, landing built with the flag)
E2E_DECK_FLOW=stdb pnpm test:e2e tests/e2e/specs/deck.spec.ts
```

Expected: both pass.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/specs/deck.spec.ts tests/e2e/playwright.config.ts
git commit -m "$(cat <<'EOF'
test(e2e): /lab/deck happy-path spec, dual-flow (legacy + stdb)

Phase 2 F4 step 6. Adds a Playwright spec that submits a brief, waits
for plan appearance, clicks generate, intercepts the download, and
verifies non-trivial zip size. Run with E2E_DECK_FLOW=legacy or =stdb
to cover both code paths; both must pass before Phase 3 cutover.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Update repo-level docs + run graphify

**Files:**
- Modify: `apps/landing/README.md` (added in Task 4 Step 1 — just confirm)
- Run: `graphify update .`

- [ ] **Step 1: Confirm `apps/landing/README.md` mentions the flag**

Already done in Task 4 Step 1. Sanity-check it landed:

```bash
grep -n NEXT_PUBLIC_USE_STDB_DECK apps/landing/README.md
```

- [ ] **Step 2: Update graphify**

```bash
graphify update .
```

Expected: graph regen succeeds with no API cost (AST-only). New nodes for `useDeckStdb`, `submitPlan`, `submitGenerate`, `downloadZipFromUrl` should appear; the deck community should pick up new INFERRED edges between Deck.tsx and the W3 reducer wrappers.

- [ ] **Step 3: Commit**

```bash
git add graphify-out/
git commit -m "$(cat <<'EOF'
chore(graphify): refresh after Phase 2 F4 deck rewire

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## F4 acceptance checklist

- [ ] `useDeckStdb` hook exists, connects with anonymous identity, persists JWT under `sastaspace.deck.anon.v1`
- [ ] `submitPlan` and `submitGenerate` use the subscribe-first pattern (subscribe in `onApplied` calls reducer)
- [ ] `Deck.tsx` has both code paths gated by `NEXT_PUBLIC_USE_STDB_DECK` — flag off behaves identically to pre-F4
- [ ] `pnpm typecheck && pnpm lint && pnpm build` clean for `apps/landing` with both flag values
- [ ] Docker compose `landing` service has the build arg wired through to `ENV` in the Dockerfile
- [ ] Manual smoke (Task 5) green for both flag states; reload-mid-render observed working at the BACKEND level (frontend state loss documented as an accepted limitation)
- [ ] `tests/e2e/specs/deck.spec.ts` passes with `E2E_DECK_FLOW=legacy` and with `E2E_DECK_FLOW=stdb`
- [ ] `apps/landing/README.md` documents the new flag and STDB env vars
- [ ] `graphify update .` ran cleanly and the new files appear in the graph

When all checked: F4 is done. Phase 3 cutover (separate plan) flips `NEXT_PUBLIC_USE_STDB_DECK=true` in the prod compose build args, rebuilds the landing image, and once stable for the canary period stops the `services/deck` Python container.

---

## Risks & follow-ups (must be flagged in the F4 PR description)

1. **Deck.tsx is large; F4 makes it larger.** The audit's M1 finding flagged Deck.tsx (1,421 lines / 51KB) for modularization. F4 adds ~50–80 lines of additive STDB-path code on top of the existing HTTP-path code. Both paths must coexist through Phase 3 by design; the redundancy is intentional. **Follow-up after Phase 4 cleanup:** split Deck.tsx into `Deck.tsx` (top-level orchestration), `Step1Idle.tsx`, `Step2Plan.tsx`, `Step3Results.tsx`, `playback.ts` (procedural Web Audio), and the existing `deckStdbFlows.ts` / `useDeckStdb.ts`. Track as a new audit-driven plan; not in scope for F4.

2. **Frontend state lost on reload mid-render.** The hook persists the *identity* across reloads, but the React state (`phase`, `plan`, `prompt`, `stdbPlanId`) is in memory only. A user who reloads during the "generating…" step sees the page at idle even though their `generate_job` row is still flipping to `done` server-side. A future enhancement: have `useDeckStdb` return the most-recent in-flight job for this identity and surface a "you have a job in progress" banner. Out of scope for F4 — the contract is "STDB rewire," not "session restoration."

3. **SDK casts in Task 1 / Task 2.** Several `as unknown as ...` and similar casts in the new files mark spots where the assumed SDK shape may not match the regenerated bindings exactly (the SDK API surface changes between minor versions). Anyone running Task 1 Step 2 / Task 2 Step 2 must inspect the actual generated `index.ts` and adapt; this is the same caveat W1/W2/W3 flagged.

4. **`zipUrl` security.** `set_generate_done` validates `zip_url.starts_with("https://")` server-side, and the worker constructs the URL from `DECK_PUBLIC_BASE_URL + jobId + ".zip"`. So no malicious URL can land in `zip_url` unless the worker itself is compromised. F4 trusts that — `downloadZipFromUrl` does no extra origin check. If audit later flags this, add a client-side `new URL(zipUrl).hostname === "deck.sastaspace.com"` guard in `downloadZipFromUrl` before fetching.

5. **Anonymous-identity rate-limiting.** The deck reducers (`request_plan`, `request_generate`) have validation on input shape but no per-identity rate limit. A bored user could spam-create rows. Out of scope for F4 (and W3 already noted it). Track as a future hardening ticket — likely a `#[reducer(scheduled)]` that prunes pending rows older than N minutes per submitter.

---

## Self-review

**Spec coverage:**
- Replace `fetch('/plan')` with `db.callReducer('request_plan', ...)` ✅ (via `submitPlan`)
- Replace `fetch('/generate')` with `db.callReducer('request_generate', ...)` ✅ (via `submitGenerate`)
- Subscribe to `plan_request` row by id (we filter by submitter+timestamp instead — same effect, simpler since the reducer doesn't return an id) ✅
- Subscribe to `generate_job` row, watch `zip_url` on done ✅
- `<a href={zipUrl} download>` style download — implemented as `downloadZipFromUrl` (fetch + Blob to preserve the existing UX; pure `<a download>` would also work but loses the "building zip…" intermediate state) ✅
- 4 UI states (drafting / queued / ready / failed) — mapped onto existing `phase` and `zipLabel` state, no new UI ✅
- Real-time, no polling — STDB subscription onUpdate ✅
- Anonymous identity, persisted in `localStorage[sastaspace.deck.anon.v1]` ✅
- Feature flag `NEXT_PUBLIC_USE_STDB_DECK`, default false until cutover ✅
- E2E spec `tests/e2e/specs/deck.spec.ts`, both flag paths ✅
- No deletion of `services/deck/` (Phase 4 owns that) ✅
- No visual/layout changes to deck UI ✅

**Coordination scan:** Touches `apps/landing/src/app/lab/deck/*` (sole owner), `infra/docker-compose.yml` `landing` service (sole owner — F1/F2/F3 modify their own service blocks), `apps/landing/Dockerfile`, `tests/e2e/specs/deck.spec.ts` (new). No conflict surface with sibling F1/F2/F3 plans. ✅

**Placeholder scan:** SDK shape caveats explicitly flagged in Task 1 Step 1 and Task 2 Step 1 (same caveat W1/W2/W3 carry — engineers verify against the regenerated bindings before shipping). E2E button selectors flagged as "verify against rendered DOM" in Task 6 Step 1. No "TBD" survives. ✅

**Type consistency:** Track type in `deckStdbFlows.ts` matches Deck.tsx's `Track` minus the client-side `id`, which matches the W3 Rust `PlannedTrack` JSON shape (with `type` not `kind` — Rust uses `#[serde(rename = "type")]`). bigint↔u64 for ids, JSON.stringify round-trips through `tracks_json: string`. ✅
