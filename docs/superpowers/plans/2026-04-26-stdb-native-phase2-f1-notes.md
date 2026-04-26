# Phase 2 F1 — Notes Auth Rewire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (run as one of 4 parallel Phase 2 workstream subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the notes app's sign-in flow off `auth.sastaspace.com` (FastAPI) onto the new STDB reducers (`request_magic_link` + `verify_token`) landed in Phase 1 W1. Both paths must coexist behind a per-app feature flag (`NEXT_PUBLIC_USE_STDB_AUTH`) until Phase 3 cutover.

**Architecture:**

Legacy path (still default after F1 lands):
```
AuthMenu → POST auth.sastaspace.com/auth/request → email → user clicks
  → auth.sastaspace.com/auth/verify?t=… → server-rendered redirect
  → notes.sastaspace.com/auth/callback#token=…&email=…
  → callback page parses fragment → saveSession()
```

New path (enabled when `NEXT_PUBLIC_USE_STDB_AUTH=true`):
```
AuthMenu → reducers.requestMagicLink(email, "notes", null, "https://notes.sastaspace.com/auth/verify")
  → auth-mailer worker drains pending_email → Resend → email
  → user clicks → notes.sastaspace.com/auth/verify?t=…
  → /auth/verify page: POST stdb /v1/identity → mint fresh JWT → reconnect
  → reducers.verifyToken(token, "")        ← reducer derives display_name from email
  → saveSession({token, email, display_name, identity})
  → redirect /
```

**Tech Stack:** TypeScript (Next.js 16, React 19), `@sastaspace/stdb-bindings` (regenerated in W1), Playwright (E2E).

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` § "Per-app frontend changes / apps/notes/" + § "Email/auth"

**Master plan:** `docs/superpowers/plans/2026-04-26-stdb-native-master.md`

**Coordination:**
- `packages/auth-ui/src/SignInModal.tsx` is shared with **typewars (F2)**. F1 changes its impl to be flag-driven so F2 inherits the new code path automatically. F2 still must add its own per-app `NEXT_PUBLIC_USE_STDB_AUTH` env wiring + verify page (typewars calls `claim_progress`, not `verify_token`, so the verify-page bodies differ — only the modal is shared).
- Do **NOT** touch `apps/notes/src/lib/auth.ts` in ways that break the FastAPI path. Branch on the feature flag only.
- Do **NOT** delete `services/auth/` — Phase 4 cleanup does that. Through Phase 3, both paths coexist and the `auth` service block in `infra/docker-compose.yml` keeps running.
- Use the **typed reducer wrappers** from `packages/stdb-bindings/src/generated/` (e.g. `reducers.requestMagicLink`). Do not hand-roll HTTP calls to STDB for the reducer invocations. The one exception is the anonymous identity mint (`POST /v1/identity`) — that's a plain `fetch` because it precedes the typed connection.

---

## Reducer signatures (from regenerated bindings — read-only reference)

From `packages/stdb-bindings/src/generated/request_magic_link_reducer.ts`:
```
email: string
app: string
prevIdentityHex: Option<string>     // pass null for notes
callbackUrl: string                  // pass "https://notes.sastaspace.com/auth/verify"
```

From `packages/stdb-bindings/src/generated/verify_token_reducer.ts`:
```
token: string
displayName: string                  // pass "" to let reducer derive from email local-part
```

The `reducers` accessor map is exported from `packages/stdb-bindings/src/generated/index.ts` as `export const reducers = __convertToAccessorMap(...)`. Per the SpacetimeDB v2.1 generator, names are camelCased (`requestMagicLink`, `verifyToken`).

---

## Task 1: Add the `NEXT_PUBLIC_USE_STDB_AUTH` feature flag plumbing

**Files:**
- Modify: `apps/notes/src/lib/auth.ts` — add flag-aware `requestMagicLink()` branch
- Create: `apps/notes/src/lib/stdbAuth.ts` — STDB-side helpers (mint identity, call reducers)

- [ ] **Step 1: Create `apps/notes/src/lib/stdbAuth.ts`**

This new module isolates the STDB-flavoured auth helpers so `auth.ts` stays thin. It hosts:
- `mintAnonymousIdentity()` — `POST {STDB_HTTP_BASE}/v1/identity` returning `{identity, token}`
- `connectWithToken(token)` — builds a fresh `DbConnection` with the JWT, returns it once `onConnect` fires
- `requestMagicLinkViaStdb(email)` — connects anon (or reuses), calls the typed `reducers.requestMagicLink`
- `verifyTokenViaStdb(token)` — does the full mint → reconnect → call sequence and returns `{jwt, email, displayName, identity}` on success

```typescript
// apps/notes/src/lib/stdbAuth.ts
//
// STDB-native auth helpers. Used when NEXT_PUBLIC_USE_STDB_AUTH=true.
// The legacy FastAPI path lives in lib/auth.ts and is unchanged.

import {
  DbConnection,
  reducers,
  type DbConnectionBuilder,
} from "@sastaspace/stdb-bindings";

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
  const body = (await r.json()) as { identity: string; token: string };
  if (!body.token || !body.identity) {
    throw new Error("mintAnonymousIdentity: missing identity/token in response");
  }
  return body;
}

/** Build a connection bound to the given JWT. Resolves on onConnect. */
export function connectWithToken(token: string | undefined): Promise<DbConnection> {
  return new Promise<DbConnection>((resolve, reject) => {
    let builder: DbConnectionBuilder = DbConnection.builder()
      .withUri(STDB_WS)
      .withModuleName(STDB_MODULE);
    if (token) builder = builder.withToken(token);
    const conn = builder
      .onConnect(() => resolve(conn))
      .onConnectError((_ctx, err) => reject(err))
      .build();
  });
}

/**
 * Anonymous flow: mint a throwaway identity, connect, call request_magic_link.
 * Resolves once the reducer call has been dispatched (not when email lands).
 */
export async function requestMagicLinkViaStdb(email: string): Promise<void> {
  const { token } = await mintAnonymousIdentity();
  const conn = await connectWithToken(token);
  try {
    await new Promise<void>((resolve, reject) => {
      const cleanup = reducers.requestMagicLink.onSuccess(() => {
        cleanup();
        errCleanup();
        resolve();
      });
      const errCleanup = reducers.requestMagicLink.onFailure((_ctx, err) => {
        cleanup();
        errCleanup();
        reject(new Error(err ?? "reducer failed"));
      });
      reducers.requestMagicLink(conn, email, "notes", null, VERIFY_CALLBACK);
    });
  } finally {
    conn.disconnect();
  }
}

/**
 * Verify flow: mint identity, connect, call verify_token, return the JWT we
 * just bound the connection to (that's the "session token" callers persist).
 *
 * displayName="" lets the reducer derive from email local-part (per W1 impl).
 */
export async function verifyTokenViaStdb(token: string): Promise<{
  jwt: string;
  identity: string;
}> {
  const minted = await mintAnonymousIdentity();
  const conn = await connectWithToken(minted.token);
  try {
    await new Promise<void>((resolve, reject) => {
      const cleanup = reducers.verifyToken.onSuccess(() => {
        cleanup();
        errCleanup();
        resolve();
      });
      const errCleanup = reducers.verifyToken.onFailure((_ctx, err) => {
        cleanup();
        errCleanup();
        reject(new Error(err ?? "verify_token failed"));
      });
      reducers.verifyToken(conn, token, "");
    });
  } finally {
    conn.disconnect();
  }
  return { jwt: minted.token, identity: minted.identity };
}
```

(`reducers.requestMagicLink.onSuccess` / `onFailure` API depends on the SDK shape exposed via `__convertToAccessorMap`. If the actual surface differs — e.g. it's `conn.reducers.requestMagicLink(...)` returning a promise, or one-shot via `conn.reducerEvents` — adapt to what `packages/stdb-bindings/src/generated/index.ts` actually exports. The shape above is the conventional pattern as of `spacetimedb` v2.1; verify against the file imported in `apps/landing/src/app/lab/deck/Deck.tsx` which already uses these reducers in a similar way after F4 lands — for F1, `git grep "reducers\\." packages/stdb-bindings/src/generated/index.ts` to confirm.)

- [ ] **Step 2: Add the flag-aware branch in `apps/notes/src/lib/auth.ts`**

Modify `requestMagicLink` to pick the path. **Do not change any other export.** Keep the storage shape (`saveSession`/`getSession`) backward-compatible — the existing FastAPI callback page must keep working unchanged.

```typescript
// At top of file, alongside existing AUTH_BASE constant:
const USE_STDB_AUTH =
  process.env.NEXT_PUBLIC_USE_STDB_AUTH === "true";
```

Replace the existing `requestMagicLink` body:

```typescript
export async function requestMagicLink(email: string): Promise<void> {
  if (USE_STDB_AUTH) {
    const { requestMagicLinkViaStdb } = await import("./stdbAuth");
    await requestMagicLinkViaStdb(email);
    return;
  }
  // Legacy FastAPI path — unchanged.
  const r = await fetch(`${AUTH_BASE}/auth/request`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email }),
  });
  if (!r.ok) {
    let detail = "";
    try {
      const data = await r.json();
      detail = typeof data.detail === "string" ? data.detail : "";
    } catch {
      /* ignore */
    }
    throw new Error(detail || `request failed (HTTP ${r.status})`);
  }
}
```

The dynamic import keeps the STDB bindings out of the legacy bundle when the flag is off.

- [ ] **Step 3: Extend `saveSession` to accept full session shape (additive)**

Add a sibling `saveFullSession` so the new verify page can persist `display_name` and `identity` directly without lossy `email.split("@")` derivation. The legacy `saveSession(token, email)` stays untouched (still used by the legacy callback page).

Append to `apps/notes/src/lib/auth.ts`:

```typescript
/**
 * Persist a session built by the STDB-native verify flow. Unlike saveSession,
 * this trusts the caller's display_name and identity rather than deriving.
 * Identity is stored for future use (e.g. profile screens); not part of
 * the legacy Session shape so existing readers continue to work.
 */
export function saveFullSession(args: {
  token: string;
  email: string;
  display_name: string;
  identity?: string;
}): Session {
  const session: Session = {
    token: args.token,
    email: args.email,
    display_name: args.display_name,
    saved_at: Date.now(),
  };
  if (typeof window !== "undefined") {
    const payload = args.identity
      ? { ...session, identity: args.identity }
      : session;
    window.localStorage.setItem(STORAGE_KEY, JSON.stringify(payload));
  }
  notify(session);
  return session;
}
```

- [ ] **Step 4: Build + typecheck**

```bash
cd apps/notes && pnpm typecheck && pnpm lint
```

Expected: clean. If `reducers.requestMagicLink.onSuccess`/`onFailure` shape mismatches, this is where the typecheck flags it — reconcile against the actual generated types before continuing.

- [ ] **Step 5: Commit**

```bash
git add apps/notes/src/lib/auth.ts apps/notes/src/lib/stdbAuth.ts
git commit -m "$(cat <<'EOF'
feat(notes): flag-aware requestMagicLink + STDB auth helpers

Phase 2 F1 step 1. Adds NEXT_PUBLIC_USE_STDB_AUTH branch in
apps/notes/src/lib/auth.ts so requestMagicLink can call the new
request_magic_link reducer instead of the FastAPI POST when the
flag is on. Default is the legacy path. Adds saveFullSession to
persist display_name + identity from the verify page.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Wire the same flag through the shared `SignInModal`

**Files:**
- Modify: `packages/auth-ui/src/SignInModal.tsx` — accept an optional `onSubmit` prop OR read flag and call reducer

**Why:** The notes app uses `AuthMenu` (its own modal — not SignInModal) for sign-in today. SignInModal is used by **typewars**. F1 still touches it because the spec calls F1 the SignInModal-rewire workstream. The cleanest move is to make SignInModal **flag-aware via injected dependency** so F1 (notes) and F2 (typewars) both benefit without duplicating the flag-branch logic.

- [ ] **Step 1: Refactor SignInModal to accept an injected submit handler**

The current `submit()` hard-codes a `fetch` to `${authBase}/auth/request`. Replace with an optional `onRequest` prop that, when provided, owns the network call. When absent, fall back to the existing fetch (legacy default).

```typescript
// packages/auth-ui/src/SignInModal.tsx — top of props interface
export interface SignInModalProps {
  app: "notes" | "typewars";
  callback: string;
  prevIdentity?: string;
  authBase?: string;
  open: boolean;
  onClose: () => void;
  /**
   * Optional override. When provided, the modal calls this with the
   * trimmed email instead of POSTing to {authBase}/auth/request. Used
   * by the STDB-native path so the modal stays presentational and the
   * reducer call lives in the consuming app.
   */
  onRequest?: (email: string) => Promise<void>;
}
```

In `submit()`, replace the `fetch` block with:

```typescript
async function submit(e: FormEvent) {
  e.preventDefault();
  setStatus("sending");
  setError(null);
  try {
    if (onRequest) {
      await onRequest(email);
    } else {
      const body: Record<string, unknown> = { email, app, callback };
      if (prevIdentity) body.prev_identity = prevIdentity;
      const r = await fetch(`${base}/auth/request`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });
      if (!r.ok) {
        const detail = await r.text().catch(() => "");
        throw new Error(detail || `HTTP ${r.status}`);
      }
    }
    setStatus("sent");
  } catch (err) {
    setStatus("error");
    setError(err instanceof Error ? err.message : "request failed");
  }
}
```

This is **purely additive** — every existing call-site that doesn't pass `onRequest` keeps the legacy POST. F2 (typewars) will pass an `onRequest` that calls `requestMagicLinkViaStdb` from the typewars app's helper.

(F1 itself doesn't change `apps/notes/src/components/AuthMenu.tsx` — the notes app uses its own modal, not SignInModal. The flag-branch in `apps/notes/src/lib/auth.ts` from Task 1 is what flips the notes path.)

- [ ] **Step 2: Typecheck**

```bash
cd packages/auth-ui && pnpm exec tsc --noEmit
# Plus the consumers:
cd apps/typewars && pnpm typecheck
cd apps/notes && pnpm typecheck
```

Expected: clean. Typewars compile must still pass even though F2 hasn't yet wired `onRequest` — the prop is optional.

- [ ] **Step 3: Commit**

```bash
git add packages/auth-ui/src/SignInModal.tsx
git commit -m "$(cat <<'EOF'
feat(auth-ui): SignInModal accepts injected onRequest handler

Phase 2 F1. Adds optional onRequest prop so the consuming app can
own the network call (reducer vs FastAPI). Legacy POST stays as
the default when onRequest is omitted. F2 (typewars) will pass an
onRequest in its own workstream; F1 only touches the modal so the
shared package is ready.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Build the new `/auth/verify` page

**Files:**
- Create: `apps/notes/src/app/auth/verify/page.tsx`
- Reference: `apps/notes/src/app/auth/callback/page.tsx` (copy layout/styling, swap behavior)

- [ ] **Step 1: Create the page**

```typescript
// apps/notes/src/app/auth/verify/page.tsx
"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { saveFullSession } from "@/lib/auth";
import { verifyTokenViaStdb } from "@/lib/stdbAuth";
import styles from "@/app/notes.module.css";

type State =
  | { kind: "loading" }
  | { kind: "ok" }
  | { kind: "error"; message: string };

function VerifyInner() {
  const params = useSearchParams();
  const [state, setState] = useState<State>({ kind: "loading" });

  useEffect(() => {
    const token = params.get("t");
    if (!token) {
      setState({
        kind: "error",
        message: "Sign-in link is incomplete (no token). Try signing in again.",
      });
      return;
    }
    let cancelled = false;
    (async () => {
      try {
        const { jwt, identity } = await verifyTokenViaStdb(token);
        if (cancelled) return;
        // The reducer derived display_name from email; we re-derive client-side
        // for the saved Session shape. Source of truth lives in the user table
        // and propagates via subscriptions.
        // Email isn't returned by the reducer call directly — read it back from
        // the token's local-part via a follow-up SQL or store-and-forward path.
        // For F1, we resolve email from the magic-link's same-origin sessionStorage
        // hint set when the modal POSTed (sessionStorage key "sastaspace.pendingEmail").
        const pendingEmail =
          typeof window !== "undefined"
            ? window.sessionStorage.getItem("sastaspace.pendingEmail") ?? ""
            : "";
        const email = pendingEmail || "user@unknown";
        const display_name = email.split("@")[0] ?? email;
        saveFullSession({ token: jwt, email, display_name, identity });
        if (typeof window !== "undefined") {
          window.sessionStorage.removeItem("sastaspace.pendingEmail");
        }
        setState({ kind: "ok" });
      } catch (err) {
        if (cancelled) return;
        const message =
          err instanceof Error ? err.message : "verify failed";
        setState({
          kind: "error",
          message: friendlyError(message),
        });
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [params]);

  useEffect(() => {
    if (state.kind !== "ok") return;
    const t = window.setTimeout(() => {
      window.location.replace("/");
    }, 600);
    return () => window.clearTimeout(t);
  }, [state]);

  return (
    <div className={styles.wrap}>
      <main style={{ padding: "96px 0 48px", textAlign: "center" }}>
        {state.kind === "loading" && (
          <p
            style={{
              color: "var(--brand-muted)",
              fontFamily: "var(--font-mono)",
              fontSize: 13,
            }}
          >
            verifying your sign-in link…
          </p>
        )}
        {state.kind === "ok" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>
              You&apos;re signed in.
            </h1>
            <p style={{ color: "var(--brand-muted)", fontSize: 14 }}>
              Redirecting to notes…
            </p>
          </>
        )}
        {state.kind === "error" && (
          <>
            <h1 style={{ fontSize: 24, fontWeight: 500, margin: "0 0 8px" }}>
              Sign-in failed.
            </h1>
            <p
              style={{
                color: "var(--brand-muted)",
                fontSize: 14,
                marginBottom: 16,
              }}
            >
              {state.message}
            </p>
            <Link href="/" style={{ color: "var(--brand-sasta-text)" }}>
              ← back to notes
            </Link>
          </>
        )}
      </main>
    </div>
  );
}

function friendlyError(raw: string): string {
  if (/expired/i.test(raw)) {
    return "That sign-in link has expired. Magic links are good for 15 minutes — request a fresh one.";
  }
  if (/already used/i.test(raw)) {
    return "That link has already been used. Request a fresh sign-in link.";
  }
  if (/unknown token/i.test(raw)) {
    return "That sign-in link doesn't look right. Try signing in again.";
  }
  return "We couldn't verify that link. Try signing in again.";
}

export default function AuthVerifyPage() {
  return (
    <Suspense fallback={null}>
      <VerifyInner />
    </Suspense>
  );
}
```

The `Suspense` wrapper is required because Next.js 16 mandates it around `useSearchParams` in client components.

- [ ] **Step 2: Stash the user's email in sessionStorage at request-time**

The verify page needs the email to populate `Session.email` (the reducer doesn't return it; subscribing to `user` table would also work but is heavier for the round-trip). Stash it when the AuthMenu submits.

Modify `apps/notes/src/components/AuthMenu.tsx` — in `onSubmit`, before the `requestMagicLink` call:

```typescript
if (typeof window !== "undefined") {
  window.sessionStorage.setItem("sastaspace.pendingEmail", value);
}
```

This is harmless for the legacy path (callback receives email in the fragment and ignores sessionStorage); harmless if user opens the link in a different browser (sessionStorage missing → fallback to `user@unknown` and the user table subscription corrects it on next mount via the existing `display_name` flow). Acceptable trade-off for F1; a follow-up could subscribe to `user WHERE identity = ctx.sender()` and read the email after verify.

- [ ] **Step 3: Build + typecheck**

```bash
cd apps/notes && pnpm typecheck && pnpm lint && pnpm build
```

Expected: clean. The build must succeed because `out/` is the deployable artifact.

- [ ] **Step 4: Commit**

```bash
git add apps/notes/src/app/auth/verify/page.tsx apps/notes/src/components/AuthMenu.tsx
git commit -m "$(cat <<'EOF'
feat(notes): /auth/verify page — STDB-native sign-in completion

Phase 2 F1. Parses ?t=<token>, mints anonymous STDB identity,
calls verify_token reducer atomically, persists session via
saveFullSession, redirects /. Friendly error messages for
expired/used/unknown tokens. AuthMenu stashes email in
sessionStorage so the verify page can populate Session.email.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Annotate the legacy `/auth/callback` page

**Files:**
- Modify: `apps/notes/src/app/auth/callback/page.tsx`

- [ ] **Step 1: Add the deprecation comment**

At the top of the file, above the existing `"use client"` directive:

```typescript
// LEGACY — slated for deletion in Phase 4.
//
// This page handles the FastAPI sign-in path: auth.sastaspace.com server-renders
// a redirect to notes.sastaspace.com/auth/callback#token=...&email=... and this
// component parses the fragment.
//
// The new STDB-native path lives in /auth/verify. Both pages coexist until the
// Phase 3 cutover stops the FastAPI auth service. Stale magic-link emails (sent
// pre-cutover, opened post-cutover) will still land here for one TTL window
// (15 minutes), so do NOT remove until Phase 4 cleanup.
//
// See docs/superpowers/plans/2026-04-26-stdb-native-master.md
```

Do **not** change any behavior. The page must keep working byte-identically through Phase 3.

- [ ] **Step 2: Commit**

```bash
git add apps/notes/src/app/auth/callback/page.tsx
git commit -m "$(cat <<'EOF'
docs(notes): annotate /auth/callback as Phase 4 deletion target

Phase 2 F1. Adds a header comment marking the legacy FastAPI
callback page for removal once /auth/verify is proven out and
in-flight magic-link TTL expires post-cutover. Behavior unchanged.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: E2E spec for the new path

**Files:**
- Create: `tests/e2e/specs/notes-auth-stdb.spec.ts`
- Modify: `tests/e2e/helpers/auth.ts` — add a `signInViaStdb(page, email)` helper

- [ ] **Step 1: Add `signInViaStdb` helper**

Append to `tests/e2e/helpers/auth.ts`:

```typescript
import { STDB_REST, STDB_DATABASE, NOTES } from "./urls.js";

/**
 * STDB-native sign-in path. Calls request_magic_link via the STDB HTTP
 * /v1/call endpoint, then reads the issued token straight out of the
 * auth_token table via SQL (test-only side door — production users get the
 * token by email). Then drives /auth/verify in the browser as a real user
 * would after clicking the email link.
 *
 * Requires the worker (auth-mailer) to NOT be running, OR the test secret
 * to be configured to suppress real Resend calls. The test reads the
 * token directly from STDB so it doesn't depend on email arrival.
 */
export async function signInViaStdb(page: Page, email: string): Promise<void> {
  const ownerToken = process.env.E2E_STDB_OWNER_TOKEN ?? "";
  // Step 1: call request_magic_link via stdb HTTP API. Anonymous identity is
  // fine — the reducer just inserts rows; auth.sastaspace.com is bypassed.
  const callRes = await page.request.post(
    `${STDB_REST}/v1/database/${STDB_DATABASE}/call/request_magic_link`,
    {
      headers: { "Content-Type": "application/json" },
      data: JSON.stringify([
        email,
        "notes",
        null,
        `${NOTES}/auth/verify`,
      ]),
    },
  );
  if (callRes.status() >= 400) {
    throw new Error(
      `request_magic_link failed: HTTP ${callRes.status()} ${await callRes.text()}`,
    );
  }
  // Step 2: read the issued token from the auth_token table.
  const rows = await sql(
    page.request,
    `SELECT token FROM auth_token WHERE email = '${email}' ORDER BY created_at DESC LIMIT 1`,
    ownerToken,
  );
  const token = rows[0]?.[0] as string | undefined;
  if (!token) throw new Error(`no auth_token row for ${email}`);
  // Step 3: drive the verify page like a real user clicking the email link.
  // Pre-stash the email in sessionStorage like AuthMenu does.
  await page.goto(`${NOTES}/`);
  await page.evaluate(
    (e) => window.sessionStorage.setItem("sastaspace.pendingEmail", e),
    email,
  );
  await page.goto(`${NOTES}/auth/verify?t=${encodeURIComponent(token)}`);
  await page.waitForURL((url) => url.toString() === `${NOTES}/`, {
    timeout: 15_000,
  });
}
```

(The `sql` import is already in scope via `helpers/stdb.ts`. Add the import: `import { sql } from "./stdb.js";` at the top if not present.)

- [ ] **Step 2: Create `tests/e2e/specs/notes-auth-stdb.spec.ts`**

```typescript
import { expect, test } from "@playwright/test";
import { readSession, signInViaStdb } from "../helpers/auth.js";
import { sql } from "../helpers/stdb.js";
import { waitForHydrate } from "../helpers/page.js";
import { NOTES, STDB_REST, STDB_DATABASE } from "../helpers/urls.js";

// These specs only run when NEXT_PUBLIC_USE_STDB_AUTH=true was baked into the
// notes deploy under test. CI sets it via the matrix in playwright.config.ts;
// locally, set E2E_STDB_AUTH=true to opt in.
test.skip(
  process.env.E2E_STDB_AUTH !== "true",
  "STDB-native auth path not enabled for this run",
);

test.describe("notes auth — STDB-native path", () => {
  test("happy path: request → verify → session in localStorage", async ({ page }) => {
    const email = `e2e-stdb-${Date.now()}@sastaspace.com`;
    await signInViaStdb(page, email);
    await waitForHydrate(page);
    const session = await readSession(page);
    expect(session).not.toBeNull();
    expect(session!.email).toBe(email);
    expect(session!.token.length).toBeGreaterThan(20);
  });

  test("expired token shows friendly error", async ({ page }) => {
    // Manually insert an expired auth_token, then drive verify with it.
    const email = `e2e-stdb-exp-${Date.now()}@sastaspace.com`;
    const token = `expired-${Date.now()}-${"x".repeat(20)}`;
    const ownerToken = process.env.E2E_STDB_OWNER_TOKEN ?? "";
    await page.request.post(
      `${STDB_REST}/v1/database/${STDB_DATABASE}/sql`,
      {
        headers: {
          "Content-Type": "text/plain",
          ...(ownerToken ? { Authorization: `Bearer ${ownerToken}` } : {}),
        },
        // Insert with expires_at in the past (1 micro = epoch+0).
        data: `INSERT INTO auth_token (token, email, created_at, expires_at, used_at) VALUES ('${token}', '${email}', 0, 1, NULL)`,
      },
    );
    await page.goto(`${NOTES}/auth/verify?t=${token}`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
    await expect(page.locator("body")).toContainText(/expired/i);
  });

  test("used token shows friendly error", async ({ page }) => {
    const email = `e2e-stdb-used-${Date.now()}@sastaspace.com`;
    await signInViaStdb(page, email);
    // First sign-in consumed the token. Re-fetch it (still in auth_token table
    // but used_at is now non-null) and try again.
    const rows = await sql(
      page.request,
      `SELECT token FROM auth_token WHERE email = '${email}' ORDER BY created_at DESC LIMIT 1`,
      process.env.E2E_STDB_OWNER_TOKEN,
    );
    const token = rows[0]?.[0] as string;
    await page.goto(`${NOTES}/auth/verify?t=${encodeURIComponent(token)}`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
    await expect(page.locator("body")).toContainText(/already used/i);
  });

  test("garbage token shows friendly error", async ({ page }) => {
    await page.goto(`${NOTES}/auth/verify?t=${"x".repeat(64)}`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
    await expect(page.locator("body")).toContainText(/doesn't look right|verify/i);
  });

  test("missing ?t shows friendly error", async ({ page }) => {
    await page.goto(`${NOTES}/auth/verify`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
    await expect(page.locator("body")).toContainText(/incomplete/i);
  });

  test("network blip mid-verify surfaces an error (mocked)", async ({ page }) => {
    // Block the /v1/identity mint endpoint to simulate a network drop.
    await page.route(`${STDB_REST}/v1/identity`, (route) => route.abort("internetdisconnected"));
    await page.goto(`${NOTES}/auth/verify?t=${"a".repeat(32)}`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
  });
});
```

- [ ] **Step 3: Run the new specs locally against a staging compose with the worker enabled**

```bash
# In one shell — compose with WORKER_AUTH_MAILER_ENABLED=true and
# notes built with NEXT_PUBLIC_USE_STDB_AUTH=true.
cd infra && WORKER_AUTH_MAILER_ENABLED=true docker compose up -d
# In another:
cd tests/e2e && \
  E2E_STDB_AUTH=true \
  E2E_BASE_NOTES=http://localhost:3001 \
  E2E_BASE_STDB=http://localhost:3100 \
  E2E_STDB_OWNER_TOKEN=$(spacetime login show --token) \
  pnpm exec playwright test specs/notes-auth-stdb.spec.ts
```

Expected: all 6 specs pass.

- [ ] **Step 4: Commit**

```bash
git add tests/e2e/specs/notes-auth-stdb.spec.ts tests/e2e/helpers/auth.ts
git commit -m "$(cat <<'EOF'
test(e2e): notes auth — STDB-native path coverage

Phase 2 F1. Adds happy path + expired/used/garbage/missing/network-blip
specs for /auth/verify against the request_magic_link → verify_token
reducer flow. Skipped unless E2E_STDB_AUTH=true so the suite stays
green on legacy-only runs. Adds signInViaStdb helper that reads
the issued token from the auth_token table directly (test-only side
door — production users get it by email).

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Run the legacy specs in matrix to prove no regression

**Files:**
- Modify: `tests/e2e/playwright.config.ts` (or equivalent) — add a project matrix

- [ ] **Step 1: Inspect the existing config**

```bash
cat tests/e2e/playwright.config.ts
```

Identify how `projects` are declared. We need two: `notes-legacy` (`E2E_STDB_AUTH=false`) and `notes-stdb` (`E2E_STDB_AUTH=true`). Both run the full suite; the legacy spec at `specs/auth.spec.ts` is unchanged, the new spec at `specs/notes-auth-stdb.spec.ts` `test.skip`s itself unless `E2E_STDB_AUTH=true`.

- [ ] **Step 2: Add the matrix entries**

In `tests/e2e/playwright.config.ts`'s `projects` array, add:

```typescript
{
  name: "notes-legacy",
  use: { ...devices["Desktop Chrome"] },
  // Default — E2E_STDB_AUTH unset, NEXT_PUBLIC_USE_STDB_AUTH unset in deploy
},
{
  name: "notes-stdb",
  use: {
    ...devices["Desktop Chrome"],
  },
  // CI sets E2E_STDB_AUTH=true and deploys notes with NEXT_PUBLIC_USE_STDB_AUTH=true
  // for this project. Legacy specs in specs/auth.spec.ts still pass because the
  // FastAPI auth service is still running; the new specs in
  // specs/notes-auth-stdb.spec.ts un-skip and exercise the new path.
},
```

(Exact shape depends on the existing config — match its style.)

- [ ] **Step 3: Update CI workflow to drive the matrix**

Inspect `.github/workflows/e2e.yml` (or whatever the workflow is) and add a strategy matrix that runs both projects. Each matrix leg sets the env vars described in Step 2 and stands up the appropriate compose.

```yaml
strategy:
  matrix:
    auth-path: [legacy, stdb]
env:
  E2E_STDB_AUTH: ${{ matrix.auth-path == 'stdb' && 'true' || 'false' }}
  NEXT_PUBLIC_USE_STDB_AUTH: ${{ matrix.auth-path == 'stdb' && 'true' || 'false' }}
```

(If the workflow file doesn't yet exist or doesn't drive E2E from CI, leave a TODO comment in `tests/e2e/README.md` describing how to run both legs locally — Phase 3 cutover wires CI fully.)

- [ ] **Step 4: Run both legs locally**

```bash
# leg 1 — legacy
cd tests/e2e && pnpm exec playwright test --project=notes-legacy
# leg 2 — stdb
E2E_STDB_AUTH=true pnpm exec playwright test --project=notes-stdb
```

Expected: both legs green. The legacy leg includes `specs/auth.spec.ts` (FastAPI path) and skips the new spec; the stdb leg runs both — `specs/auth.spec.ts` still passes because the FastAPI service is still up, AND the new spec runs.

- [ ] **Step 5: Commit**

```bash
git add tests/e2e/playwright.config.ts .github/workflows/
git commit -m "$(cat <<'EOF'
test(e2e): matrix legacy + stdb auth paths for notes

Phase 2 F1. Adds notes-legacy + notes-stdb projects so CI proves
both code paths green on every PR. Legacy spec runs in both legs
(FastAPI service still up through Phase 3); STDB-native spec runs
only when E2E_STDB_AUTH=true.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Verification — full E2E + lint + build

**Files:** none (verification only)

- [ ] **Step 1: Notes app build passes with both flag values**

```bash
cd apps/notes
NEXT_PUBLIC_USE_STDB_AUTH=false pnpm build && rm -rf .next out
NEXT_PUBLIC_USE_STDB_AUTH=true  pnpm build && rm -rf .next out
```

Expected: both succeed.

- [ ] **Step 2: Lint + typecheck across touched packages**

```bash
cd apps/notes && pnpm typecheck && pnpm lint
cd packages/auth-ui && pnpm exec tsc --noEmit
cd packages/stdb-bindings && pnpm exec tsc --noEmit  # sanity-check bindings unaffected
```

Expected: clean.

- [ ] **Step 3: Full Playwright suite, both legs**

```bash
cd tests/e2e
pnpm exec playwright test --project=notes-legacy
E2E_STDB_AUTH=true pnpm exec playwright test --project=notes-stdb
```

Expected: both green. No regressions in any non-auth spec (`comments-anon`, `comments-signed-in`, `notes`, `landing`, `typewars-*`, `admin`).

- [ ] **Step 4: Smoke-test in browser manually**

```bash
# Compose up with worker enabled and notes built with the flag on
NEXT_PUBLIC_USE_STDB_AUTH=true pnpm --filter @sastaspace/notes dev
# Visit http://localhost:3001, click "sign in", enter an email
# In another shell:
spacetime sql sastaspace "SELECT id, to_email, status FROM pending_email ORDER BY id DESC LIMIT 5"
# Should show the queued (or sent — if RESEND_API_KEY is real) row.
# Copy the issued token:
spacetime sql sastaspace "SELECT token FROM auth_token ORDER BY created_at DESC LIMIT 1"
# Visit http://localhost:3001/auth/verify?t=<token>
# Should land back at / with the AuthMenu showing "signed in as <local-part>"
```

Expected: end-to-end browser flow works. localStorage `sastaspace.auth.v1` populated. AuthMenu shows the email local-part.

- [ ] **Step 5: graphify update**

```bash
graphify update .
```

Expected: graph reflects the new files (`apps/notes/src/lib/stdbAuth.ts`, `apps/notes/src/app/auth/verify/page.tsx`).

- [ ] **Step 6: Commit verification artefacts (if any)**

If `graphify update` produces diffs in `graphify-out/`:

```bash
git add graphify-out/
git commit -m "$(cat <<'EOF'
chore(graphify): refresh after Phase 2 F1 notes auth rewire

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## F1 acceptance checklist

- [ ] `apps/notes/src/lib/auth.ts` branches on `NEXT_PUBLIC_USE_STDB_AUTH`; legacy POST untouched when flag is false
- [ ] `apps/notes/src/lib/stdbAuth.ts` exists with `mintAnonymousIdentity`, `connectWithToken`, `requestMagicLinkViaStdb`, `verifyTokenViaStdb`
- [ ] `apps/notes/src/app/auth/verify/page.tsx` exists; handles happy + expired + used + garbage + missing-token + network-blip with friendly UI
- [ ] `apps/notes/src/app/auth/callback/page.tsx` carries the Phase 4 deletion comment but is otherwise unchanged
- [ ] `packages/auth-ui/src/SignInModal.tsx` accepts an optional `onRequest` prop; legacy POST is the default when omitted
- [ ] `tests/e2e/specs/notes-auth-stdb.spec.ts` covers happy + expired + used + garbage + missing + network-blip
- [ ] `tests/e2e/playwright.config.ts` runs `notes-legacy` + `notes-stdb` projects; both green
- [ ] `apps/notes` builds cleanly with both `NEXT_PUBLIC_USE_STDB_AUTH=true` and `=false`
- [ ] No production traffic flipped — flag remains `false` in `infra/docker-compose.yml` until Phase 3 cutover
- [ ] `services/auth/` is untouched (Phase 4 cleanup deletes it)

When all checked: F1 is done. Cutover to flip `NEXT_PUBLIC_USE_STDB_AUTH=true` on prod happens in Phase 3.

---

## Self-review

**Spec coverage:**
- Sign-in flow swap on SignInModal + auth.ts: ✅ (Tasks 1–2)
- New `/auth/verify` page with mint → reconnect → verify: ✅ (Task 3)
- Behind `NEXT_PUBLIC_USE_STDB_AUTH` flag, default false: ✅ (Tasks 1, 6)
- Legacy `/auth/callback` retained with deletion-target comment: ✅ (Task 4)
- E2E for happy + expired + used + network-blip + bad-token: ✅ (Task 5)
- Matrix runs both legacy and stdb paths: ✅ (Task 6)

**Coordination risks (called out in plan header, restated):**
- `packages/auth-ui/src/SignInModal.tsx` is shared with typewars (F2). F1 changes the modal additively (new optional prop). F2 will pass that prop. Risk: parallel F1/F2 execution merge-conflicts the modal file. Mitigation: F1 lands the additive prop change first; F2 rebases trivially. If both PRs touch the file, the conflict is in the small `submit()` body — easy to resolve.
- The notes app uses its **own** AuthMenu, not SignInModal. F1's flag-branch in `apps/notes/src/lib/auth.ts` is what flips notes between paths. SignInModal changes are for F2's benefit. This separation is intentional per the spec but worth re-confirming with the human reviewer if SignInModal was meant to replace AuthMenu (it was not, per current code).

**Placeholder scan:**
- `reducers.requestMagicLink.onSuccess`/`onFailure` shape acknowledged as version-dependent in Task 1 Step 1 with an instruction to verify against generated bindings before implementation. ✅
- `tests/e2e/playwright.config.ts` matrix syntax in Task 6 Step 2 noted as "match the existing style" because the actual config file shape isn't in the plan. ✅
- `.github/workflows/e2e.yml` adjustments in Task 6 Step 3 marked as "if the file doesn't yet exist, leave a TODO" — F1 doesn't block on CI being fully wired; Phase 3 owns that. ✅
- `friendlyError()` in the verify page maps known reducer error strings (`"token expired"`, `"token already used"`, `"unknown token"`) to user-friendly copy. These match exactly the strings returned by W1's `verify_token` reducer. ✅

**Type consistency:**
- `request_magic_link` arg names from generated bindings (`email`, `app`, `prevIdentityHex`, `callbackUrl`) match call-site in `requestMagicLinkViaStdb`. ✅
- `verify_token` arg names (`token`, `displayName`) match call-site in `verifyTokenViaStdb`; passing `""` for displayName is per W1 reducer's documented behavior of deriving from email. ✅
- `Session` shape in `apps/notes/src/lib/auth.ts` is unchanged for legacy compatibility; `saveFullSession` is additive and writes the same keys plus optional `identity`. ✅
