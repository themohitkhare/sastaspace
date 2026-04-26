/**
 * Magic-link helpers — two backends, switched by env:
 *
 *   E2E_AUTH_BACKEND=fastapi   (default, back-compat) — POST /auth/request
 *                              on auth.sastaspace.com with X-Test-Secret;
 *                              the FastAPI side door returns the token in
 *                              the JSON body.
 *
 *   E2E_AUTH_BACKEND=stdb      — call the `mint_test_token(email, secret)`
 *                              reducer on the sastaspace STDB module. The
 *                              reducer is owner+secret gated; the helper
 *                              uses E2E_STDB_OWNER_TOKEN as the bearer
 *                              auth and E2E_TEST_SECRET as the second arg.
 *                              The minted token is read back via SQL from
 *                              the private `last_test_token` table.
 *
 * The exported `signIn(page, email)` is the new wrapper — it branches on
 * E2E_AUTH_BACKEND and routes to either path. The legacy FastAPI flow is
 * preserved exactly under `signInViaFastapi` so existing specs that
 * import `signIn` keep working both before AND after Phase 3 cutover —
 * just toggle the env.
 */

import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { AUTH, NOTES, TYPEWARS, STDB_REST, STDB_DATABASE } from "./urls.js";
import { sql } from "./stdb.js";

const TEST_SECRET = process.env.E2E_TEST_SECRET ?? "";
const AUTH_BACKEND = (process.env.E2E_AUTH_BACKEND ?? "fastapi").toLowerCase();

type AuthApp = "notes" | "typewars";

interface TokenOptions {
  app?: AuthApp;
  callback?: string;
  prevIdentity?: string;
}

export async function requestTokenViaTestMode(
  request: APIRequestContext,
  email: string,
  opts: TokenOptions = {},
): Promise<string> {
  if (!TEST_SECRET) {
    throw new Error(
      "E2E_TEST_SECRET env var is required for sign-in tests. Set it in the local shell or via GH Actions secret.",
    );
  }
  const data: Record<string, string> = { email };
  if (opts.app) data.app = opts.app;
  if (opts.callback) data.callback = opts.callback;
  if (opts.prevIdentity) data.prev_identity = opts.prevIdentity;
  const r = await request.post(`${AUTH}/auth/request`, {
    data,
    headers: {
      "Content-Type": "application/json",
      "X-Test-Secret": TEST_SECRET,
    },
  });
  expect(r.status(), `auth/request returned ${r.status()} for ${email}`).toBe(200);
  const body = await r.json();
  expect(body.test_token, "expected test_token in response").toBeTruthy();
  return body.test_token as string;
}

/**
 * Drive the full magic-link flow against the live UI via the legacy
 * FastAPI side door:
 *   1. POST /auth/request with the test secret → get the token
 *   2. Navigate to /auth/verify?t=<token> on auth.sastaspace.com
 *   3. The verify page does a window.location.replace to
 *      notes.sastaspace.com/auth/callback#token=...
 *   4. The callback page parses the fragment, saves the session, redirects to /
 *
 * After this, page.context().url() will be NOTES + "/" (or close to it)
 * and localStorage will contain the session under sastaspace.auth.v1.
 *
 * This is the back-compat path. The dispatching `signIn` wrapper below
 * routes here when E2E_AUTH_BACKEND is unset or "fastapi".
 */
export async function signInViaFastapi(page: Page, email: string): Promise<void> {
  const token = await requestTokenViaTestMode(page.request, email);
  // Navigate to the verify URL — same flow a real user would have via
  // the email link.
  await page.goto(`${AUTH}/auth/verify?t=${encodeURIComponent(token)}`);
  // The verify HTML uses window.location.replace to the callback. Wait for
  // the redirect chain to settle on a notes URL.
  await page.waitForURL((url) => url.toString().startsWith(NOTES), {
    timeout: 15_000,
  });
}

/**
 * Drive the magic-link flow for typewars. If `prevIdentity` is supplied (e.g.
 * after registerPlayer wired up an anon player row), it's forwarded to the
 * auth side door so the verify endpoint can stitch claim_progress.
 *
 * If no explicit `prevIdentity` is supplied, the helper attempts to recover
 * one from the current `typewars:auth_token` JWT in localStorage (the
 * spacetime client stamps a `sub` / `identity` claim there). This unblocks
 * the typewars-auth.spec.ts case where a prior `registerPlayer` step has
 * implicitly minted a guest identity but the test author didn't thread it
 * through manually.
 *
 * Works for both auth paths:
 *   - legacy FastAPI: ?t=<token>&app=typewars[&prev=<hex>] → /auth/verify on
 *     auth.sastaspace.com → window.location.replace to TYPEWARS/auth/callback
 *   - STDB-native:    same URL shape; the typewars build's NEXT_PUBLIC_USE_STDB_AUTH
 *     flag picks the verify-page implementation
 */
export async function signInTypewars(
  page: Page,
  email: string,
  opts: { prevIdentity?: string } = {},
): Promise<void> {
  let prevIdentity = opts.prevIdentity;
  if (!prevIdentity) {
    prevIdentity = (await page.evaluate(() => {
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
    })) as string | undefined;
  }

  const token = await requestTokenViaTestMode(page.request, email, {
    app: "typewars",
    callback: `${TYPEWARS}/auth/callback`,
    prevIdentity,
  });
  const prevQs = prevIdentity
    ? `&prev=${encodeURIComponent(prevIdentity)}`
    : "";
  await page.goto(
    `${AUTH}/auth/verify?t=${encodeURIComponent(token)}&app=typewars${prevQs}`,
  );
  // Verify page does window.location.replace to TYPEWARS/auth/callback#token=...
  // which then router.replace("/")s into the SPA.
  await page.waitForURL((url) => url.toString().startsWith(TYPEWARS), {
    timeout: 15_000,
  });
}

export async function signOut(page: Page): Promise<void> {
  await page.evaluate(() => window.localStorage.removeItem("sastaspace.auth.v1"));
}

export async function readSession(page: Page): Promise<{
  token: string;
  email: string;
  display_name: string;
} | null> {
  return page.evaluate(() => {
    const raw = window.localStorage.getItem("sastaspace.auth.v1");
    return raw ? (JSON.parse(raw) as never) : null;
  });
}

/**
 * STDB-native sign-in path. Calls the `mint_test_token(email, secret)`
 * reducer on the sastaspace module, reads the minted token back from
 * the private `last_test_token` table via owner-JWT SQL, then drives the
 * app's `/auth/verify?t=<token>` page like a real user clicking the
 * email link.
 *
 * The reducer is owner-AND-secret gated — see
 * modules/sastaspace/src/lib.rs `mint_test_token` for the gating logic.
 * In production the owner JWT is owner-only and the secret row is
 * absent, so the side door fails closed with "test mode disabled".
 *
 * Required env:
 *   - E2E_TEST_SECRET        the secret installed via
 *                            `set_e2e_test_secret` post-publish
 *   - E2E_STDB_OWNER_TOKEN   the owner JWT (`spacetime login show --token`)
 *
 * The reducer's `assert_owner` check requires the bearer to be the
 * owner identity. The minted `auth_token` row has the same shape as
 * one produced by `request_magic_link` (15-minute TTL), so the existing
 * `verify_token` reducer consumes it unchanged.
 */
export async function signInViaStdb(page: Page, email: string): Promise<void> {
  if (!TEST_SECRET) {
    throw new Error(
      "E2E_TEST_SECRET env var is required for STDB sign-in tests. Set it (and run `set_e2e_test_secret` on the module) before running.",
    );
  }
  const ownerToken = process.env.E2E_STDB_OWNER_TOKEN ?? "";
  if (!ownerToken) {
    throw new Error(
      "E2E_STDB_OWNER_TOKEN env var is required for STDB sign-in tests (the mint_test_token reducer is assert_owner-gated).",
    );
  }
  // Step 1: call mint_test_token via the STDB HTTP API with the owner JWT.
  // The reducer asserts owner AND secret-match, then upserts the minted
  // token into the `last_test_token` singleton (because STDB 2.1 reducers
  // can't return values to the caller).
  const callRes = await page.request.post(
    `${STDB_REST}/v1/database/${STDB_DATABASE}/call/mint_test_token`,
    {
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${ownerToken}`,
      },
      data: JSON.stringify([email, TEST_SECRET]),
    },
  );
  if (callRes.status() >= 400) {
    throw new Error(
      `mint_test_token failed: HTTP ${callRes.status()} ${await callRes.text()}`,
    );
  }
  // Step 2: read the minted token from `last_test_token`. We filter by
  // email so a racing test (different email, same instant) can't steal
  // the row. SQL strings are owner-only here so we can use single-row
  // table semantics safely.
  const rows = await sql(
    page.request,
    `SELECT token FROM last_test_token WHERE email = '${email.replace(/'/g, "''")}' LIMIT 1`,
    ownerToken,
  );
  const token = rows[0]?.[0] as string | undefined;
  if (!token) {
    throw new Error(
      `no last_test_token row for ${email} after mint_test_token call`,
    );
  }
  // Step 3: drive the verify page like a real user clicking the email link.
  // The app under test (notes / typewars / admin) is responsible for the
  // /auth/verify route — F1's frontend work wires that up. Pre-stash the
  // email in sessionStorage like AuthMenu does so the verify page can
  // populate Session.email correctly.
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

/**
 * Dispatching wrapper. Routes to the legacy FastAPI helper or the
 * STDB-native helper depending on E2E_AUTH_BACKEND. Existing specs that
 * import `signIn` get the new path automatically once the env is set.
 *
 *   E2E_AUTH_BACKEND=stdb     → signInViaStdb
 *   E2E_AUTH_BACKEND=fastapi  → signInViaFastapi (default, back-compat)
 *
 * Anything else throws so a typo doesn't silently fall back to the wrong
 * backend.
 */
export async function signIn(page: Page, email: string): Promise<void> {
  if (AUTH_BACKEND === "stdb") {
    await signInViaStdb(page, email);
    return;
  }
  if (AUTH_BACKEND === "fastapi") {
    await signInViaFastapi(page, email);
    return;
  }
  throw new Error(
    `unknown E2E_AUTH_BACKEND='${AUTH_BACKEND}' (expected 'stdb' or 'fastapi')`,
  );
}
