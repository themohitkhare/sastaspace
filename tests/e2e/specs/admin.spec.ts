import { expect, test } from "@playwright/test";
import { signIn } from "../helpers/auth.js";
import { NOTES } from "../helpers/urls.js";

const OWNER_EMAIL = process.env.E2E_OWNER_EMAIL ?? "mohitkhare582@gmail.com";

test.describe("admin queue — owner gating", () => {
  test("not signed in → admin page shows the gate, not the queue", async ({ page }) => {
    await page.goto(`${NOTES}/admin/comments`);
    await expect(page.getByRole("heading", { name: /comment queue/i })).toBeVisible();
    await expect(page.locator("text=/sign in.*owner/i")).toBeVisible();
    // No row controls
    await expect(page.locator("button", { hasText: /^approve$/ })).toHaveCount(0);
  });

  test("signed in as non-owner → page rejects with stranger-email message", async ({ page }) => {
    const email = `e2e-stranger-${Date.now()}@sastaspace.com`;
    await signIn(page, email);
    await page.goto(`${NOTES}/admin/comments`);
    await expect(page.locator("text=/only the lab owner can moderate/i")).toBeVisible();
  });

  test("signed in as owner → page connects + shows queue UI", async ({ page }) => {
    // Seed a comment as a fresh signed-in user so it lands as `pending`
    // and the moderator flips it to `approved`/`flagged`. Anon posting
    // is no longer supported (gated for spam reasons).
    const probeEmail = `e2e-probe-${Date.now()}@sastaspace.com`;
    const localPart = probeEmail.split("@")[0];
    const slug = "2026-04-25-hello";

    await signIn(page, probeEmail);
    await page.goto(`${NOTES}/${slug}`);
    const body = `BUY CHEAP MEDS NOW NOW http://spam.example admin-probe`;
    await page.getByRole("textbox", { name: /^comment$/i }).fill(body);
    await page.getByRole("button", { name: /post comment/i }).click();
    await expect(page.getByText(/moderator's looking it over/i)).toBeVisible({
      timeout: 15_000,
    });
    // Give the moderator time to process (≈3s poll + ≈1.5s classify)
    await new Promise((r) => setTimeout(r, 6_000));

    // Now sign in as owner and check the admin queue
    await signIn(page, OWNER_EMAIL);
    await page.goto(`${NOTES}/admin/comments`);
    await expect(page.getByRole("heading", { name: /comment queue/i })).toBeVisible();
    // The owner-authenticated stdb subscription has to do a HTTPS fetch
    // to /v1/identity/websocket-token (CSP must allow https://stdb…) —
    // give it generous time for the WS handshake + subscription apply.
    await expect(page.locator(`text=${localPart}`)).toBeVisible({ timeout: 20_000 });
  });
});
