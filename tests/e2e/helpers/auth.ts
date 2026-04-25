/**
 * Magic-link helpers using the auth service's E2E side door.
 *
 * `requestTokenViaTestMode` calls /auth/request with the X-Test-Secret
 * header that the auth service knows about. Server-side, that bypasses
 * Resend and returns the issued token directly. Tests then drive
 * /auth/verify themselves and complete the callback.
 */

import { expect, type APIRequestContext, type Page } from "@playwright/test";
import { AUTH, NOTES } from "./urls.js";

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
