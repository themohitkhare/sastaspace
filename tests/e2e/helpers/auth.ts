/**
 * Magic-link helpers using the auth service's E2E side door.
 *
 * `requestTokenViaTestMode` calls /auth/request with the X-Test-Secret
 * header that the auth service knows about. Server-side, that bypasses
 * Resend and returns the issued token directly. Tests then drive
 * /auth/verify themselves and complete the callback.
 */

import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { AUTH, NOTES, STDB_REST, STDB_DATABASE } from "./urls.js";
import { sql } from "./stdb.js";

const TEST_SECRET = process.env.E2E_TEST_SECRET ?? "";

export async function requestTokenViaTestMode(
  request: APIRequestContext,
  email: string,
): Promise<string> {
  if (!TEST_SECRET) {
    throw new Error(
      "E2E_TEST_SECRET env var is required for sign-in tests. Set it in the local shell or via GH Actions secret.",
    );
  }
  const r = await request.post(`${AUTH}/auth/request`, {
    data: { email },
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
 * STDB-native sign-in path. Calls request_magic_link via the STDB HTTP
 * /v1/call endpoint, then reads the issued token straight out of the
 * auth_token table via SQL (test-only side door — production users get the
 * token by email). Then drives /auth/verify in the browser as a real user
 * would after clicking the email link.
 *
 * Requires the worker (auth-mailer) to NOT be running in test mode that would
 * actually email, OR the test secret to be configured to suppress real Resend
 * calls. The test reads the token directly from STDB so it doesn't depend on
 * email arrival.
 */
export async function signInViaStdb(page: Page, email: string): Promise<void> {
  const ownerToken = process.env.E2E_STDB_OWNER_TOKEN ?? "";
  // Step 1: call request_magic_link via the STDB HTTP API. An anonymous
  // identity is fine — the reducer just inserts rows; auth.sastaspace.com
  // is bypassed entirely.
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
  // Pre-stash the email in sessionStorage like AuthMenu does so the verify
  // page can populate Session.email correctly.
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
