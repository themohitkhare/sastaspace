# Phase 2 F2 — Typewars Auth Frontend Rewire Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (run as one of 4 parallel Phase 2 workstream subagents). Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move the typewars sign-in from the FastAPI `services/auth/` round-trip into a client-side flow that calls the new STDB reducers (`request_magic_link`, `verify_token`) on the **sastaspace** module and then transfers guest progress on the **typewars** module via the existing `claim_progress` reducer. Both legacy and rewired paths coexist behind `NEXT_PUBLIC_USE_STDB_AUTH`.

**Architecture:**
1. `SignInModal` (shared `@sastaspace/auth-ui`) was switched to call `request_magic_link` on the sastaspace module by F1 (notes). F2 just consumes that swap by setting `NEXT_PUBLIC_USE_STDB_AUTH=true` on the typewars build. Typewars passes `app="typewars"` and `prev_identity_hex=<current guest identity hex>` so the reducer bakes `?prev=<hex>` into the magic-link URL.
2. New `apps/typewars/src/app/auth/verify/page.tsx` reads `?t=<token>&app=typewars&prev=<hex>` from the URL, mints a fresh identity via `POST /v1/identity` against STDB, reconnects to the **sastaspace** module with the new JWT, calls `verify_token(token, displayName)` to consume the token + register the User row, then reconnects to the **typewars** module and calls `claim_progress(prev_identity, new_identity, email)` to transfer the guest's stats.
3. Existing `apps/typewars/src/app/auth/callback/page.tsx` stays alive for one release per the spec (legacy fragment-based callback after FastAPI redirect) — F2 only adds a `// PHASE 4 DELETE` marker comment.
4. The user has untracked WIP at `tests/e2e/specs/typewars-auth.spec.ts` and `tests/e2e/helpers/auth.ts:73-84` that was failing in Phase 0 baseline because `signInTypewars` does not pass `prev_identity` to the auth side-door. F2 owns the helper fix.

**Tech Stack:** TypeScript (Next.js 15 client component, fetch, `@sastaspace/stdb-bindings`, `@sastaspace/typewars-bindings`), Playwright (E2E).

**Spec:** `docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md` § "Per-app frontend changes / apps/typewars/" + § "Email/auth" reducers note about `verify_token_typewars`.

**Master plan:** `docs/superpowers/plans/2026-04-26-stdb-native-master.md`

**Coordination:**
- F1 (notes) modifies `packages/auth-ui/src/SignInModal.tsx` to swap fetch for the reducer call. F2 does NOT touch that file — it consumes the swap via the per-app `NEXT_PUBLIC_USE_STDB_AUTH` flag that F1 introduces. If F2 races ahead of F1, defer the modal-swap step until F1 lands and rebase.
- F2 only consumes existing reducers (`request_magic_link` + `verify_token` on sastaspace, `claim_progress` on typewars). **Does not modify either Rust module.**
- The legacy FastAPI auth flow stays running in compose; both paths coexist through Phase 3.
- Untracked typewars WIP specs (`typewars-*.spec.ts`) + helpers belong to F2's narrow blast radius; touch only what's required for the prev_identity bug + the new verify-page flow.

---

## Task 1: Wire `NEXT_PUBLIC_USE_STDB_AUTH` flag into typewars `SignInTrigger`

**Files:**
- Modify: `apps/typewars/src/components/SignInTrigger.tsx`
- Modify: `apps/typewars/.env.example` (or create if missing)

- [ ] **Step 1: Read the SignInModal swap that F1 introduces**

Confirm F1 has merged its change to `packages/auth-ui/src/SignInModal.tsx` before starting this task. The modal now accepts a new prop (per F1 plan) such as `useStdb?: boolean` or it auto-detects via `NEXT_PUBLIC_USE_STDB_AUTH` inside the modal. Read the merged F1 file to confirm the contract before writing typewars code:

```bash
grep -n "USE_STDB_AUTH\|useStdb\|callReducer" packages/auth-ui/src/SignInModal.tsx
```

Adapt the wiring below to match the actual prop name F1 chose.

- [ ] **Step 2: Pass the flag into `SignInTrigger`**

Modify `apps/typewars/src/components/SignInTrigger.tsx`:

```tsx
"use client";
import { useState } from "react";
import { useSpacetimeDB } from "spacetimedb/react";
import { SignInModal } from "@sastaspace/auth-ui";

const USE_STDB_AUTH = process.env.NEXT_PUBLIC_USE_STDB_AUTH === "true";

export function SignInTrigger() {
  const { identity } = useSpacetimeDB();
  const [open, setOpen] = useState(false);
  // Identity hex without the 0x prefix — the reducer accepts either, but the
  // legacy FastAPI auth service strips it anyway, so we keep the existing shape.
  const prevIdentity = identity ? identity.toHexString() : undefined;

  return (
    <>
      <button className="link-btn" onClick={() => setOpen(true)}>sign in →</button>
      <SignInModal
        app="typewars"
        callback={
          USE_STDB_AUTH
            ? "https://typewars.sastaspace.com/auth/verify"
            : "https://typewars.sastaspace.com/auth/callback"
        }
        prevIdentity={prevIdentity}
        useStdb={USE_STDB_AUTH}
        open={open}
        onClose={() => setOpen(false)}
      />
    </>
  );
}
```

(If F1 chose a different prop name than `useStdb`, substitute it. If F1 made the modal read the env var internally, drop the prop entirely.)

- [ ] **Step 3: Add the env flag to `apps/typewars/.env.example`**

Append:

```
# Phase 2 F2: when "true", sign-in routes through the STDB reducer flow
# (request_magic_link + /auth/verify). When "false" or absent, the legacy
# FastAPI auth.sastaspace.com flow runs. Default to "false" until cutover.
NEXT_PUBLIC_USE_STDB_AUTH=false
```

- [ ] **Step 4: Build to confirm no TS errors**

```bash
cd apps/typewars && pnpm build
```

Expected: clean build. Both code paths typecheck.

- [ ] **Step 5: Commit**

```bash
git add apps/typewars/src/components/SignInTrigger.tsx apps/typewars/.env.example
git commit -m "$(cat <<'EOF'
feat(typewars): NEXT_PUBLIC_USE_STDB_AUTH flag in SignInTrigger

Phase 2 F2. Routes the magic-link callback to /auth/verify (STDB path)
when the flag is true, /auth/callback (legacy FastAPI path) when false.
Both paths coexist through Phase 3.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 2: Add `apps/typewars/src/app/auth/verify/page.tsx`

**Files:**
- Create: `apps/typewars/src/app/auth/verify/page.tsx`

- [ ] **Step 1: Write the verify page**

```tsx
"use client";
import { useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { DbConnection as SastaConn } from "@sastaspace/stdb-bindings";
import { DbConnection as TypewarsConn } from "@sastaspace/typewars-bindings";

const TOKEN_KEY = "typewars:auth_token";
const STDB_HTTP =
  process.env.NEXT_PUBLIC_STDB_HTTP ?? "https://stdb.sastaspace.com";
const STDB_WS =
  process.env.NEXT_PUBLIC_STDB_URI ?? "wss://stdb.sastaspace.com";
const SASTA_MODULE =
  process.env.NEXT_PUBLIC_SASTA_MODULE ?? "sastaspace";
const TYPEWARS_MODULE =
  process.env.NEXT_PUBLIC_TYPEWARS_MODULE ?? "typewars";

type Phase =
  | "minting"
  | "verifying"
  | "claiming"
  | "done"
  | "error"
  | "claim-warn";

export default function AuthVerifyPage() {
  const router = useRouter();
  const params = useSearchParams();
  const [phase, setPhase] = useState<Phase>("minting");
  const [message, setMessage] = useState("Minting fresh identity…");
  const [warn, setWarn] = useState<string | null>(null);

  useEffect(() => {
    const token = params.get("t");
    const app = params.get("app");
    const prev = params.get("prev"); // hex without 0x
    if (!token || app !== "typewars") {
      setPhase("error");
      setMessage("Sign-in link is missing required fields.");
      return;
    }

    let cancelled = false;
    let sastaConn: { disconnect: () => void } | null = null;
    let typewarsConn: { disconnect: () => void } | null = null;

    (async () => {
      try {
        // 1. Mint a fresh identity + JWT (anonymous HTTP; no auth header).
        setPhase("minting");
        setMessage("Minting fresh identity…");
        const identityRes = await fetch(`${STDB_HTTP}/v1/identity`, {
          method: "POST",
        });
        if (!identityRes.ok) {
          throw new Error(`identity mint failed: HTTP ${identityRes.status}`);
        }
        const { identity, token: jwt } = (await identityRes.json()) as {
          identity: string;
          token: string;
        };
        if (!jwt || !identity) {
          throw new Error("identity response missing token/identity");
        }
        if (cancelled) return;

        // 2. Connect to sastaspace module with new JWT, call verify_token.
        setPhase("verifying");
        setMessage("Verifying your sign-in link…");
        sastaConn = await new Promise<{ disconnect: () => void }>(
          (resolve, reject) => {
            const c = SastaConn.builder()
              .withUri(STDB_WS)
              .withDatabaseName(SASTA_MODULE)
              .withToken(jwt)
              .onConnect(() => resolve(c as unknown as { disconnect: () => void }))
              .onConnectError((_ctx: unknown, err: unknown) => reject(err))
              .build();
          },
        );
        const displayName = ""; // verify_token derives from email if blank
        // The generated reducer accessor is camelCased: verifyToken.
        // If your bindings expose it under a different shape, adapt.
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        await (sastaConn as any).reducers.verifyToken(token, displayName);
        if (cancelled) return;

        // 3. Reconnect to typewars module with same JWT, call claim_progress.
        setPhase("claiming");
        setMessage("Transferring your guest progress…");
        typewarsConn = await new Promise<{ disconnect: () => void }>(
          (resolve, reject) => {
            const c = TypewarsConn.builder()
              .withUri(STDB_WS)
              .withDatabaseName(TYPEWARS_MODULE)
              .withToken(jwt)
              .onConnect(() => resolve(c as unknown as { disconnect: () => void }))
              .onConnectError((_ctx: unknown, err: unknown) => reject(err))
              .build();
          },
        );

        if (prev && prev.length >= 32) {
          try {
            // claim_progress expects: prevIdentity, newIdentity, email.
            // The current sender (=newIdentity) is implicit in ctx.sender(); we
            // still pass it explicitly to match the reducer signature exposed by
            // the generated bindings. Email comes back from verify_token via the
            // user table — we read the email param from the auth_token row server-
            // side by passing it through; the simplest path is to derive the email
            // from the URL is not available, so the reducer accepts the email
            // directly. We re-derive on the server side via the User row keyed
            // on the new identity (verify_token wrote it).
            //
            // NOTE: claim_progress is owner-only on the typewars module today
            // (modules/typewars/src/player.rs:108-120). The current sender here
            // is the user, NOT the owner — this call WILL fail with "not
            // authorized" until either:
            //   (a) the typewars module is changed to allow self-claim, or
            //   (b) a `verify_token_typewars` reducer is added per the spec
            //       § Email/auth note that wraps claim_progress, or
            //   (c) the worker (auth-mailer or a new claimer) makes the call
            //       with owner credentials after observing the verify event.
            // This plan assumes option (b) lands in a follow-up workstream
            // (Phase 1 W1 addendum) before F2 ships to prod. See "Open
            // questions" at the bottom.
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            const reducers = (typewarsConn as any).reducers;
            // Read email from the user row we just registered. Subscribe briefly.
            // For now we accept the email as a side-effect of verify_token having
            // written the User row keyed on `identity` — we ask the typewars
            // claim_progress to tolerate fetching email from the User row by
            // passing the empty string and letting the reducer look up. If the
            // current claim_progress signature still requires the email arg,
            // we'd need either the wrapper reducer or to surface the email back
            // from verify_token. Until the wrapper lands, we pass an empty
            // string and surface the failure as a non-fatal warning.
            await reducers.claimProgress(prev, identity, "");
          } catch (e) {
            setWarn(
              "We couldn't transfer your guest stats — you're signed in but starting fresh on the leaderboard. " +
                String(e).slice(0, 200),
            );
            setPhase("claim-warn");
          }
        } else {
          setWarn(null);
        }

        // 4. Persist JWT under the typewars-specific key and redirect home.
        try {
          window.localStorage.setItem(TOKEN_KEY, jwt);
        } catch {
          throw new Error("localStorage blocked — sign-in cannot complete");
        }

        if (cancelled) return;
        setPhase((p) => (p === "claim-warn" ? p : "done"));
        setMessage("Signed in. Redirecting…");
        // Brief pause so the warning (if any) is readable, then go home.
        setTimeout(() => router.replace("/"), warn ? 2500 : 50);
      } catch (e) {
        if (cancelled) return;
        setPhase("error");
        setMessage(
          `Sign-in failed: ${e instanceof Error ? e.message : String(e)}`,
        );
      }
    })();

    return () => {
      cancelled = true;
      try { sastaConn?.disconnect(); } catch {}
      try { typewarsConn?.disconnect(); } catch {}
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div
      className="page"
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        minHeight: "100vh",
      }}
    >
      <div style={{ textAlign: "center", maxWidth: 480, padding: 24 }}>
        <p className="ss-eyebrow">~/typewars/auth/verify —</p>
        <p className="ss-body" style={{ marginTop: 8 }}>{message}</p>
        {warn && (
          <p
            className="ss-small"
            style={{ marginTop: 12, color: "var(--brand-muted)" }}
          >
            {warn}
          </p>
        )}
        {phase === "error" && (
          <button
            className="enlist-btn"
            onClick={() => router.replace("/")}
            style={{ marginTop: 16 }}
          >
            back to map →
          </button>
        )}
      </div>
    </div>
  );
}
```

- [ ] **Step 2: Build**

```bash
cd apps/typewars && pnpm build
```

Expected: clean build. The Next.js 15 router picks up the new route.

- [ ] **Step 3: Smoke test against local STDB (manual)**

With LocalStdb running and `NEXT_PUBLIC_USE_STDB_AUTH=true`:

```bash
# In one shell:
cd apps/typewars && NEXT_PUBLIC_USE_STDB_AUTH=true pnpm dev

# In another, queue a magic link and grab the token from the pending_email body:
spacetime call --server local sastaspace request_magic_link \
  '["smoke@example.com", "typewars", null, "http://localhost:3000/auth/verify"]'
spacetime sql sastaspace "SELECT to_email, body_text FROM pending_email ORDER BY id DESC LIMIT 1"
# Copy the t=<token> out of body_text, then visit:
#   http://localhost:3000/auth/verify?t=<token>&app=typewars
```

Expected: the page transitions minting → verifying → done, redirects to `/`, `localStorage.typewars:auth_token` is populated, the user row appears in `spacetime sql sastaspace "SELECT * FROM user"`. With a `&prev=<some-hex>` appended, the claim path runs (and either succeeds or warns per the open question below).

- [ ] **Step 4: Commit**

```bash
git add apps/typewars/src/app/auth/verify/page.tsx
git commit -m "$(cat <<'EOF'
feat(typewars): /auth/verify page calls STDB reducers directly

Phase 2 F2. Mints fresh identity via STDB, calls verify_token on the
sastaspace module to register the User, then calls claim_progress on
the typewars module to transfer guest stats. Stores JWT under the
typewars:auth_token localStorage key and redirects home. claim_progress
failures are surfaced as a non-fatal warning so sign-in still completes.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 3: Mark legacy `auth/callback/page.tsx` for Phase 4 deletion

**Files:**
- Modify: `apps/typewars/src/app/auth/callback/page.tsx`

- [ ] **Step 1: Add a deprecation comment at the top**

Prepend the file with:

```tsx
// PHASE 4 DELETE — legacy FastAPI fragment-based callback. Kept alive for
// one release per docs/superpowers/specs/2026-04-26-spacetimedb-native-design.md
// § "/auth/callback page (which handles JWT-from-fragment after the FastAPI
// redirect) gets retired once /auth/verify is live". Cutover happens in
// Phase 3; this file is git rm'd in Phase 4 cleanup.
```

Do not change any runtime behavior in this file — it must keep working for users whose magic link in flight at cutover time still routes through the FastAPI redirect.

- [ ] **Step 2: Commit**

```bash
git add apps/typewars/src/app/auth/callback/page.tsx
git commit -m "$(cat <<'EOF'
chore(typewars): mark legacy /auth/callback for Phase 4 deletion

Phase 2 F2. Comment-only change. Behavior preserved so in-flight magic
links from the FastAPI service keep working through cutover.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 4: Fix the `signInTypewars` helper for the prev_identity bug

**Files:**
- Modify: `tests/e2e/helpers/auth.ts` (lines 73-84 specifically)

- [ ] **Step 1: Update the helper to thread `prev_identity` through both code paths**

Per the Phase 0 baseline note, the user's untracked WIP `tests/e2e/specs/typewars-auth.spec.ts` was failing because `signInTypewars` did not pass `prev_identity` to the auth side door even when the test had registered a guest player. Replace the function:

```typescript
/**
 * Drive the magic-link flow for typewars. If `prevIdentity` is supplied (e.g.
 * after registerPlayer wired up an anon player row), it's forwarded to the
 * auth side door so the verify endpoint can stitch claim_progress.
 *
 * For the new STDB-native path (NEXT_PUBLIC_USE_STDB_AUTH=true), the same
 * URL shape works — the verify page reads ?prev=<hex> from the URL, which
 * the reducer-baked magic link contains.
 */
export async function signInTypewars(
  page: Page,
  email: string,
  opts: { prevIdentity?: string } = {},
): Promise<void> {
  // If the caller didn't pass prev_identity, attempt to read it from the
  // typewars connection token in localStorage. The spacetime client stamps
  // the identity onto window when the connection is live; tests that already
  // ran registerPlayer should have one.
  let prevIdentity = opts.prevIdentity;
  if (!prevIdentity) {
    prevIdentity = await page.evaluate(() => {
      // SpacetimeDB identity is exposed via the React provider context, but
      // tests can't reach into React. Fall back to the auth_token JWT — it
      // contains a `sub` claim with the identity hex.
      const tok = window.localStorage.getItem("typewars:auth_token");
      if (!tok) return undefined;
      try {
        const payload = JSON.parse(
          atob(tok.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")),
        ) as { sub?: string; identity?: string };
        return payload.sub ?? payload.identity ?? undefined;
      } catch {
        return undefined;
      }
    }) as string | undefined;
  }

  const token = await requestTokenViaTestMode(page.request, email, {
    app: "typewars",
    callback: `${TYPEWARS}/auth/callback`,
    prevIdentity,
  });
  const prevQs = prevIdentity ? `&prev=${encodeURIComponent(prevIdentity)}` : "";
  await page.goto(
    `${AUTH}/auth/verify?t=${encodeURIComponent(token)}&app=typewars${prevQs}`,
  );
  // verify page does window.location.replace to TYPEWARS/auth/callback#token=...
  // which then router.replace("/")s into the SPA.
  await page.waitForURL((url) => url.toString().startsWith(TYPEWARS), {
    timeout: 15_000,
  });
}
```

- [ ] **Step 2: Run the existing typewars-auth spec to confirm the helper unblocks it**

```bash
cd tests/e2e && pnpm playwright test typewars-auth.spec.ts
```

Expected: the three existing scenarios (`anon player sees 'sign in →' button`, `magic-link round trip stores JWT`, `/auth/callback with no fragment shows friendly error`) all pass against the **legacy** FastAPI path.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/helpers/auth.ts
git commit -m "$(cat <<'EOF'
fix(e2e): signInTypewars threads prev_identity through magic-link flow

Phase 2 F2. The helper now reads the typewars JWT's identity claim (or
accepts an explicit prevIdentity arg) and forwards it to the auth side
door + the verify URL. Unblocks tests/e2e/specs/typewars-auth.spec.ts
which were failing in Phase 0 baseline because the helper dropped the
prev_identity that registerPlayer had implicitly created.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 5: Extend typewars-auth spec to cover both legacy + STDB paths

**Files:**
- Modify: `tests/e2e/specs/typewars-auth.spec.ts`

- [ ] **Step 1: Wrap the existing magic-link test in a matrix over the env flag**

```typescript
import { expect, test } from "@playwright/test";
import { signInTypewars } from "../helpers/auth.js";
import {
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
} from "../helpers/typewars.js";
import { TYPEWARS } from "../helpers/urls.js";

const PATHS = [
  { name: "legacy FastAPI callback", env: "false" as const },
  { name: "STDB-native /auth/verify", env: "true" as const },
] as const;

test.describe("typewars · SignInTrigger + auth callback", () => {
  test("anon player sees 'sign in →' button in MapWarMap header", async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);
    await registerPlayer(page, "Wardens", randomCallsign());
    await expect(page.getByRole("button", { name: /sign in/i })).toBeVisible();
  });

  for (const path of PATHS) {
    test(`magic-link round trip via ${path.name} stores JWT and lands on warmap`, async ({
      page,
      context,
    }) => {
      // Per-test env override for the typewars build. Playwright reads the env
      // at fixture init; for runtime override of NEXT_PUBLIC_*, the typewars
      // dev server must be started with the right value, OR the test injects
      // the flag via window.__SS_FLAGS before navigation. We use the latter.
      await context.addInitScript((envFlag) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).__NEXT_PUBLIC_USE_STDB_AUTH = envFlag;
      }, path.env);

      await freshContext(page);
      await gotoTypewars(page);
      const callsign = randomCallsign();
      await registerPlayer(page, "The Codex", callsign);

      const email = `e2e-tw-${path.env}-${Date.now()}@sastaspace.com`;
      await signInTypewars(page, email);

      // JWT under typewars:auth_token regardless of path — the new verify page
      // writes the same key (apps/typewars/src/lib/spacetime.ts:8).
      const token = await page.evaluate(() =>
        window.localStorage.getItem("typewars:auth_token"),
      );
      expect(token, "JWT should be stored in localStorage").toBeTruthy();
      expect(token!.length).toBeGreaterThan(20);
      expect(page.url().startsWith(TYPEWARS)).toBe(true);
    });

    test(`prev_identity claim path via ${path.name}: guest stats survive sign-in`, async ({
      page,
      context,
    }) => {
      await context.addInitScript((envFlag) => {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (window as any).__NEXT_PUBLIC_USE_STDB_AUTH = envFlag;
      }, path.env);

      await freshContext(page);
      await gotoTypewars(page);
      const callsign = randomCallsign("claim");
      await registerPlayer(page, "Wardens", callsign);

      // Capture pre-claim identity so we can assert the post-claim row keeps
      // the same callsign / damage. Pull from the SpacetimeDB connection's
      // identity exposed on window (Battle component sets this for debugging).
      const prevIdentity = await page.evaluate(() =>
        window.localStorage.getItem("typewars:auth_token"),
      );
      expect(prevIdentity).toBeTruthy();

      const email = `e2e-tw-claim-${path.env}-${Date.now()}@sastaspace.com`;
      await signInTypewars(page, email);

      // Player row keyed on the new identity should have the same callsign.
      // (Read via UI: the warmap's profile pill shows the callsign.)
      await expect(page.getByText(new RegExp(callsign, "i"))).toBeVisible({
        timeout: 10_000,
      });
    });
  }

  test("/auth/callback with no fragment shows friendly error", async ({ page }) => {
    await page.goto(`${TYPEWARS}/auth/callback`);
    await expect(page.getByText(/missing sign-in details/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /back to map/i })).toBeVisible();
  });

  test("STDB /auth/verify with bad token shows error and back-to-map button", async ({
    page,
    context,
  }) => {
    await context.addInitScript(() => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      (window as any).__NEXT_PUBLIC_USE_STDB_AUTH = "true";
    });
    await page.goto(`${TYPEWARS}/auth/verify?t=notarealtoken&app=typewars`);
    await expect(page.getByText(/sign-in failed/i)).toBeVisible({
      timeout: 10_000,
    });
    await expect(page.getByRole("button", { name: /back to map/i })).toBeVisible();
  });
});
```

(Note: `window.__NEXT_PUBLIC_USE_STDB_AUTH` is a stand-in for whatever runtime override mechanism the typewars build supports. Next.js bakes `NEXT_PUBLIC_*` at build time, so for true matrix testing the CI must build typewars twice (once per flag value) and run each spec subset against each. The simpler near-term approach: run the legacy matrix in the existing CI job, and add a second CI job that builds typewars with `NEXT_PUBLIC_USE_STDB_AUTH=true` and runs the STDB-flagged scenarios. Adapt the spec's `addInitScript` accordingly when implementing — it's not the final shape, just the intent.)

- [ ] **Step 2: Run the spec**

```bash
cd tests/e2e && pnpm playwright test typewars-auth.spec.ts
```

Expected (against a stack with both code paths available): all scenarios green. If the STDB-path scenarios fail because the typewars build wasn't compiled with `NEXT_PUBLIC_USE_STDB_AUTH=true`, document the build-matrix requirement in the spec's preamble and skip the STDB scenarios with `test.skip` until CI is wired.

- [ ] **Step 3: Commit**

```bash
git add tests/e2e/specs/typewars-auth.spec.ts
git commit -m "$(cat <<'EOF'
test(e2e): typewars-auth covers legacy + STDB-native paths and claim flow

Phase 2 F2. Adds matrix over NEXT_PUBLIC_USE_STDB_AUTH covering happy
path + prev_identity claim + bad-token error. Documents the build-matrix
requirement for true Next.js NEXT_PUBLIC_* override.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 6: Update `apps/typewars/src/lib/spacetime.ts` doc comment for the dual JWT source

**Files:**
- Modify: `apps/typewars/src/lib/spacetime.ts`

- [ ] **Step 1: Annotate the TOKEN_KEY constant**

Add a comment above `const TOKEN_KEY = 'typewars:auth_token';`:

```typescript
// JWT lives here regardless of which auth path issued it:
//   - legacy FastAPI flow: callback page writes after parsing the URL fragment
//   - STDB-native flow:    /auth/verify writes after verify_token + claim_progress
// Both flows store the same raw JWT minted by spacetime's POST /v1/identity,
// so spacetime.ts doesn't need to know which path produced it.
const TOKEN_KEY = 'typewars:auth_token';
```

This is documentation only — no behavioral change.

- [ ] **Step 2: Commit**

```bash
git add apps/typewars/src/lib/spacetime.ts
git commit -m "$(cat <<'EOF'
docs(typewars): annotate auth_token key for dual sign-in paths

Phase 2 F2. Comment-only.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

## Task 7: Run the full typewars E2E suite against both paths

- [ ] **Step 1: Legacy path baseline**

```bash
cd tests/e2e && pnpm playwright test typewars-auth typewars-battle typewars-leaderboard typewars-legion-swap typewars-profile typewars-register typewars-warmap
```

Expected: all green against the legacy path (default flag). This proves F2 didn't break the existing flow.

- [ ] **Step 2: STDB path verification**

Rebuild typewars with `NEXT_PUBLIC_USE_STDB_AUTH=true` and re-run the auth-touching specs:

```bash
cd apps/typewars && NEXT_PUBLIC_USE_STDB_AUTH=true pnpm build
# (Or restart the dev server with the env var)
cd ../../tests/e2e && pnpm playwright test typewars-auth typewars-profile
```

Expected: green against the STDB-native path.

- [ ] **Step 3: Capture timing baseline**

Note the wall-clock for the magic-link round-trip on each path. The STDB path adds two STDB connection round-trips (mint + verify reconnect + claim reconnect); expect ~+500ms over the legacy path. If the gap exceeds 3 s, file a follow-up to consolidate the two reconnects into a single connection.

- [ ] **Step 4: Final commit if any spec edits were needed during the run**

```bash
git add tests/e2e/
git commit -m "$(cat <<'EOF'
test(e2e): minor adjustments after typewars E2E full-suite verification

Phase 2 F2 acceptance run.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
EOF
)"
```

(Skip if no changes were needed.)

---

## F2 acceptance checklist

- [ ] `NEXT_PUBLIC_USE_STDB_AUTH=false`: full typewars E2E suite green against legacy FastAPI auth
- [ ] `NEXT_PUBLIC_USE_STDB_AUTH=true`: typewars-auth + typewars-profile specs green against STDB-native auth
- [ ] `apps/typewars/src/app/auth/verify/page.tsx` exists and successfully drives mint → verify_token → claim_progress → localStorage → redirect
- [ ] `apps/typewars/src/app/auth/callback/page.tsx` carries the `PHASE 4 DELETE` marker but is otherwise unchanged
- [ ] `tests/e2e/helpers/auth.ts` `signInTypewars` reads / accepts `prevIdentity` and forwards it through both URL surfaces
- [ ] `packages/auth-ui/src/SignInModal.tsx` is **not** touched by F2 (owned by F1)
- [ ] `modules/typewars/src/*.rs` is **not** touched by F2 (no new reducers added)
- [ ] No production traffic flipped; the flag stays `false` in compose until Phase 3 cutover

When all checked: F2 is done. Phase 3 cutover flips the flag on prod after the auth-mailer worker is healthy.

---

## Open questions

1. **`claim_progress` is owner-only — how does the user-side `/auth/verify` actually call it?**
   The spec § "Email/auth" mentions a `verify_token_typewars(token, prev_identity_hex, display_name)` reducer in `modules/typewars/` that wraps `claim_progress`. The task description for F2 says "Don't touch the typewars module's Rust code." These conflict. The plan above assumes one of:
   - **(a)** A small follow-up to Phase 1 W1 adds `verify_token_typewars` to `modules/typewars/src/lib.rs` that the F2 verify page calls instead of `claim_progress` directly. **Recommended** — minimal Rust delta, preserves owner-gating semantics, lets F2 stay in the frontend lane.
   - **(b)** `claim_progress` is relaxed to allow self-claim when `ctx.sender() == new_identity`. Surface area on `modules/typewars/` but small.
   - **(c)** The auth-mailer worker (or a new worker) observes verify_token completions and calls `claim_progress` server-side with owner credentials. Adds latency and a new subscription, more moving parts.
   **Decision needed before F2 ships.** The plan codes the call as if (a) lands.

2. **`claim_progress` requires `email` as an argument — how does the verify page know it?**
   The current reducer signature in `packages/typewars-bindings/src/generated/claim_progress_reducer.ts` takes `prevIdentity, newIdentity, email`. The verify page only has the token until verify_token consumes it; the email lives on the `auth_token` row server-side. Options:
   - The wrapper from open-question 1(a) reads the email from `auth_token` server-side and only takes `(token, prev_identity_hex, display_name)` from the client.
   - The verify page subscribes to the `User` table after `verify_token` and reads its own row's email before calling `claim_progress`. Adds another round-trip.
   - The verify page parses the email out of the original magic-link URL (FastAPI used to put it in the fragment; the reducer-built URL currently does not).
   The plan above passes `""` as email and notes this needs follow-up.

3. **Build-time vs runtime flag for `NEXT_PUBLIC_USE_STDB_AUTH`.**
   Next.js bakes `NEXT_PUBLIC_*` at build, so the matrix in Task 5 needs either two builds in CI or a runtime override hatch. Easiest: add a single CI job that builds typewars twice (once per flag value), runs each spec subset against the right build. Confirm with infra before coding the CI matrix.

4. **`typewars:auth_token` lives directly as a JWT string today, but the notes app uses a JSON envelope (`sastaspace.auth.v1`).** Should F2 unify on the envelope shape so future code can read display_name without round-tripping STDB? **Default:** keep typewars's bare-JWT shape — F2 is migration-only, not refactor.

5. **Does the `/auth/verify` page need to handle the case where the user's browser already has a `typewars:auth_token`?** (e.g. user clicks the magic-link in a browser that's already signed in to a different account.) The legacy callback overwrites blindly. F2's verify page should do the same for parity — no extra logic needed, but call out as an unchanged-from-legacy decision.

---

## Self-review

**Spec coverage:** spec calls for `request_magic_link` swap ✅ (via SignInModal flag), new `/auth/verify` page ✅, `claim_progress` invocation ✅ (with caveat per open-question 1), legacy callback retained for one release ✅, dual-path E2E ✅, helper fix for prev_identity ✅. All covered. ✅

**Placeholder scan:** Open questions 1, 2, 3 are flagged explicitly above — the plan codes the most likely shape with comments calling out the assumption. No silent TBDs. ✅

**Coordination check:** Does NOT touch `packages/auth-ui/src/SignInModal.tsx` (F1 owns), does NOT touch `modules/typewars/src/*.rs` (Phase 1 W1 follow-up owns per open-question 1), does NOT touch `apps/notes/` (F1 owns). ✅

**Type consistency:** `verify_token` reducer signature `(token: string, displayName: string)` matches the verify page call. `claim_progress` signature `(prevIdentity, newIdentity, email)` per `packages/typewars-bindings/src/generated/claim_progress_reducer.ts` — matches the page call **except for the email-discovery question** flagged in open-question 2. ✅
