import { expect, test } from "@playwright/test";
import { signIn } from "../helpers/auth.js";
import { sql } from "../helpers/stdb.js";
import { NOTES } from "../helpers/urls.js";

const OWNER_EMAIL = process.env.E2E_OWNER_EMAIL ?? "mohitkhare582@gmail.com";

test.describe("admin queue — owner gating", () => {
  test.afterEach(async ({ request }) => {
    await sql(
      request,
      `DELETE FROM comment WHERE author_name = 'E2EAdminProbe'`,
    ).catch(() => {});
  });

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

  test("signed in as owner → page connects + shows queue UI", async ({ page, request }) => {
    // Seed a flagged comment so the queue has a known row to render
    const slug = "2026-04-25-hello";
    // Submit an anon comment first so the moderator processes it
    await page.goto(`${NOTES}/${slug}`);
    await page
      .getByLabel(/name/i)
      .fill("E2EAdminProbe");
    const body = `BUY CHEAP MEDS NOW NOW http://spam.example admin-probe`;
    await page.getByRole("textbox", { name: /comment/i }).fill(body);
    await page.getByRole("button", { name: /post comment/i }).click();
    // Wait for moderator to flag it
    await new Promise((r) => setTimeout(r, 6_000));

    // Now sign in as owner and check the admin queue
    await signIn(page, OWNER_EMAIL);
    await page.goto(`${NOTES}/admin/comments`);
    await expect(page.getByRole("heading", { name: /comment queue/i })).toBeVisible();
    // Eventually the seeded comment should show up
    await expect(page.locator("text=E2EAdminProbe")).toBeVisible({ timeout: 15_000 });
  });
});
