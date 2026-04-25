import { expect, test } from "@playwright/test";
import { readSession, requestTokenViaTestMode, signIn } from "../helpers/auth.js";
import { gotoAndHydrate, waitForHydrate } from "../helpers/page.js";
import { AUTH, NOTES } from "../helpers/urls.js";

test.describe("auth — magic-link round trip", () => {
  test("/auth/request with test secret returns a token (test-mode side door)", async ({
    request,
  }) => {
    const token = await requestTokenViaTestMode(request, `e2e-${Date.now()}@sastaspace.com`);
    expect(token.length).toBeGreaterThanOrEqual(32);
  });

  test("/auth/verify with valid token redirects through to notes/auth/callback", async ({
    page,
  }) => {
    const token = await requestTokenViaTestMode(page.request, `e2e-${Date.now()}@sastaspace.com`);
    await page.goto(`${AUTH}/auth/verify?t=${encodeURIComponent(token)}`);
    await page.waitForURL((url) => url.toString().startsWith(NOTES), { timeout: 15_000 });
  });

  test("/auth/verify with garbage token shows friendly error (no RetryError repr)", async ({
    page,
  }) => {
    await page.goto(`${AUTH}/auth/verify?t=${"x".repeat(64)}`);
    await expect(page.getByRole("heading", { name: /sign-in failed/i })).toBeVisible();
    await expect(page.locator("body")).not.toContainText(/RetryError|Future at 0x/);
  });

  test("full sign-in: magic link → callback → session in localStorage", async ({ page }) => {
    const email = `e2e-flow-${Date.now()}@sastaspace.com`;
    await signIn(page, email);
    expect(page.url()).toMatch(new RegExp(`^${NOTES}`));
    const session = await readSession(page);
    expect(session).not.toBeNull();
    expect(session!.email).toBe(email);
    expect(session!.token.length).toBeGreaterThan(20);
  });

  test("after sign-in, AuthMenu shows display_name and 'sign out'", async ({ page }) => {
    const email = `e2e-menu-${Date.now()}@sastaspace.com`;
    await signIn(page, email);
    await waitForHydrate(page);
    const localPart = email.split("@")[0];
    // Scope to the nav so the same name in a comment doesn't collide
    const nav = page.locator("nav[aria-label='Primary']");
    await expect(nav.getByText(localPart, { exact: true })).toBeVisible();
    await expect(nav.getByRole("button", { name: /sign out/i })).toBeVisible();
  });

  test("sign-out clears the session", async ({ page }) => {
    const email = `e2e-out-${Date.now()}@sastaspace.com`;
    await signIn(page, email);
    await waitForHydrate(page);
    const nav = page.locator("nav[aria-label='Primary']");
    await nav.getByRole("button", { name: /sign out/i }).click();
    await expect(nav.getByRole("button", { name: /sign in/i })).toBeVisible();
    expect(await readSession(page)).toBeNull();
  });
});
