import { expect, test } from "@playwright/test";
import { signIn } from "../helpers/auth.js";
import { gotoAndHydrate, waitForHydrate } from "../helpers/page.js";
import { sql } from "../helpers/stdb.js";
import { NOTES } from "../helpers/urls.js";

test.describe("comments — signed-in user", () => {
  test.afterEach(async ({ request }) => {
    await sql(request, `DELETE FROM comment WHERE author_name LIKE 'e2e-user-%'`).catch(() => {});
  });

  test("CommentForm replaces name field with 'posting as <display_name>'", async ({ page }) => {
    const email = `e2e-user-${Date.now()}@sastaspace.com`;
    const localPart = email.split("@")[0];

    await signIn(page, email);
    await waitForHydrate(page);
    // Open a post
    await page.locator('a[href^="/2026-"]').first().click();
    await page.waitForURL(/\/2026-/);
    await waitForHydrate(page);

    // Form should NOT have a free-form name field
    await expect(page.getByLabel(/^name/i)).not.toBeVisible();
    // Should show the "posting as <name>" indicator inside the comments section
    const commentsRegion = page.locator("section[aria-label='Comments']");
    await expect(commentsRegion.locator("text=/posting as/i")).toBeVisible();
    // The display_name appears INSIDE comments region as <strong>
    await expect(commentsRegion.locator("strong", { hasText: localPart })).toBeVisible();
  });

  test("signed-in comment uses User.display_name on the published row", async ({ page, request }) => {
    const email = `e2e-user-${Date.now()}@sastaspace.com`;
    const localPart = email.split("@")[0];

    await signIn(page, email);
    await waitForHydrate(page);
    await page.locator('a[href^="/2026-"]').first().click();
    await page.waitForURL(/\/2026-/);
    await waitForHydrate(page);
    const slug = page.url().split("/").pop()!;

    const body = `signed-in e2e at ${new Date().toISOString()}`;
    await page.getByRole("textbox", { name: /^comment$/i }).fill(body);
    await page.getByRole("button", { name: /post comment/i }).click();
    await expect(page.getByText(/moderator's looking it over/i)).toBeVisible({
      timeout: 15_000,
    });

    // Verify in stdb: row exists with author_name == local-part of email
    let rows: unknown[][] = [];
    for (let i = 0; i < 15; i++) {
      rows = await sql(
        request,
        `SELECT author_name FROM comment WHERE post_slug = '${slug}' AND author_name = '${localPart}'`,
      );
      if (rows.length > 0) break;
      await new Promise((r) => setTimeout(r, 1_000));
    }
    expect(rows.length).toBeGreaterThan(0);
    expect(String(rows[0][0]).replace(/"/g, "")).toBe(localPart);
  });
});
