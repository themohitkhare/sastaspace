// E2E coverage for the STDB-native sign-in path on the notes app.
//
// These specs only run when the notes deploy under test was built with
// NEXT_PUBLIC_USE_STDB_AUTH=true. Locally, set E2E_STDB_AUTH=true to opt in;
// CI sets it via the matrix in playwright.config.ts.
//
// The signInViaStdb helper bypasses email by reading the issued token
// straight out of the auth_token table after dispatching request_magic_link.

import { expect, test } from "@playwright/test";
import { readSession, signInViaStdb } from "../helpers/auth.js";
import { sql } from "../helpers/stdb.js";
import { waitForHydrate } from "../helpers/page.js";
import { NOTES, STDB_REST, STDB_DATABASE } from "../helpers/urls.js";

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
    const insertRes = await page.request.post(
      `${STDB_REST}/v1/database/${STDB_DATABASE}/sql`,
      {
        headers: {
          "Content-Type": "text/plain",
          ...(ownerToken ? { Authorization: `Bearer ${ownerToken}` } : {}),
        },
        // Insert with expires_at in the past (epoch+1µs).
        data: `INSERT INTO auth_token (token, email, created_at, expires_at, used_at) VALUES ('${token}', '${email}', 0, 1, NULL)`,
      },
    );
    if (insertRes.status() >= 400) {
      throw new Error(
        `expired-token insert failed: HTTP ${insertRes.status()} ${await insertRes.text()}`,
      );
    }
    await page.goto(`${NOTES}/auth/verify?t=${token}`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
    await expect(page.locator("body")).toContainText(/expired/i);
  });

  test("used token shows friendly error", async ({ page }) => {
    const email = `e2e-stdb-used-${Date.now()}@sastaspace.com`;
    await signInViaStdb(page, email);
    // First sign-in consumed the token. Re-fetch it (still in auth_token
    // table but used_at is now non-null) and try again.
    const rows = await sql(
      page.request,
      `SELECT token FROM auth_token WHERE email = '${email}' ORDER BY created_at DESC LIMIT 1`,
      process.env.E2E_STDB_OWNER_TOKEN,
    );
    const token = rows[0]?.[0] as string;
    expect(token, "expected to retrieve the consumed token").toBeTruthy();
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
    await expect(page.locator("body")).toContainText(
      /doesn't look right|verify|verify/i,
    );
  });

  test("missing ?t shows friendly error", async ({ page }) => {
    await page.goto(`${NOTES}/auth/verify`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
    await expect(page.locator("body")).toContainText(/incomplete/i);
  });

  test("network blip mid-verify surfaces an error (mocked)", async ({ page }) => {
    // Block the /v1/identity mint endpoint to simulate a network drop. The
    // verify page should surface a friendly error instead of hanging in
    // the loading state.
    await page.route(`${STDB_REST}/v1/identity`, (route) =>
      route.abort("internetdisconnected"),
    );
    await page.goto(`${NOTES}/auth/verify?t=${"a".repeat(32)}`);
    await expect(
      page.getByRole("heading", { name: /sign-in failed/i }),
    ).toBeVisible();
  });
});
