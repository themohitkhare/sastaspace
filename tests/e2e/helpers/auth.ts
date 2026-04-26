/**
 * Magic-link helpers using the auth service's E2E side door.
 *
 * `requestTokenViaTestMode` calls /auth/request with the X-Test-Secret
 * header that the auth service knows about. Server-side, that bypasses
 * Resend and returns the issued token directly. Tests then drive
 * /auth/verify themselves and complete the callback.
 */

import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { AUTH, NOTES, TYPEWARS } from "./urls.js";

const TEST_SECRET = process.env.E2E_TEST_SECRET ?? "";

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
 * Drive the full magic-link flow against the live UI:
 *   1. POST /auth/request with the test secret → get the token
 *   2. Navigate to /auth/verify?t=<token> on auth.sastaspace.com
 *   3. The verify page does a window.location.replace to
 *      notes.sastaspace.com/auth/callback#token=...
 *   4. The callback page parses the fragment, saves the session, redirects to /
 *
 * After this, page.context().url() will be NOTES + "/" (or close to it)
 * and localStorage will contain the session under sastaspace.auth.v1.
 */
export async function signIn(page: Page, email: string): Promise<void> {
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
