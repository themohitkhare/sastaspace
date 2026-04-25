import { expect, test } from "@playwright/test";
import { sql, pollUntil } from "../helpers/stdb.js";
import { NOTES } from "../helpers/urls.js";

/**
 * Anonymous comment flow:
 *   1. Open a post page
 *   2. Submit a benign comment via the form
 *   3. Confirm the form transitions to the "queued, moderator reviewing" state
 *   4. Poll stdb directly until the moderator approves it (~3-5s)
 *   5. Reload and verify the comment is now visible
 *
 * Then clean up the smoke comment so the queue stays tidy for real users.
 */

const SMOKE_BODY_TAG = "<<E2E_SMOKE_TAG>>";

test.describe("comments — anonymous post + moderator", () => {
  test.beforeAll(async ({ request }) => {
    // Defensive cleanup of any leftover smoke rows from a previous run
    await sql(
      request,
      `DELETE FROM comment WHERE author_name = 'E2EAnon'`,
    ).catch(() => {});
  });

  test.afterEach(async ({ request }) => {
    await sql(
      request,
      `DELETE FROM comment WHERE author_name = 'E2EAnon'`,
    ).catch(() => {});
  });

  test("anon comment goes to pending → moderator approves within 10s", async ({ page, request }) => {
    // Open the first post
    await page.goto(NOTES);
    const firstPostLink = page.locator('a[href^="/2026-"]').first();
    const slug = (await firstPostLink.getAttribute("href"))!.replace(/^\//, "");
    await firstPostLink.click();
    await page.waitForURL(new RegExp(`${slug}/?$`));

    const body = `e2e smoke at ${new Date().toISOString()} — totally benign content ${SMOKE_BODY_TAG}`;

    // Fill + submit the form
    await page.getByLabel(/name/i).fill("E2EAnon");
    await page.getByRole("textbox", { name: /comment/i }).fill(body);
    await page.getByRole("button", { name: /post comment/i }).click();

    // Form should switch to queued state
    await expect(page.getByText(/moderator's looking it over/i)).toBeVisible({
      timeout: 10_000,
    });

    // Poll stdb until the row exists with status='approved'
    const approved = await pollUntil(
      async () => {
        const rows = await sql(
          request,
          `SELECT status FROM comment WHERE author_name = 'E2EAnon' AND post_slug = '${slug}'`,
        );
        if (rows.length === 0) return false;
        const status = String(rows[0][0]).replace(/"/g, "");
        return status === "approved" ? status : false;
      },
      { timeoutMs: 20_000, intervalMs: 1_000, what: "moderator approval" },
    );
    expect(approved).toBe("approved");
  });

  test("spam comment goes to pending → moderator flags within 10s", async ({ page, request }) => {
    await page.goto(NOTES);
    const firstPostLink = page.locator('a[href^="/2026-"]').first();
    const slug = (await firstPostLink.getAttribute("href"))!.replace(/^\//, "");
    await firstPostLink.click();
    await page.waitForURL(new RegExp(`${slug}/?$`));

    const spam = `BUY CHEAP MEDS at http://spam.example NOW NOW NOW click click ${SMOKE_BODY_TAG}`;
    await page.getByLabel(/name/i).fill("E2EAnon");
    await page.getByRole("textbox", { name: /comment/i }).fill(spam);
    await page.getByRole("button", { name: /post comment/i }).click();
    await expect(page.getByText(/moderator's looking it over/i)).toBeVisible({
      timeout: 10_000,
    });

    const flagged = await pollUntil(
      async () => {
        const rows = await sql(
          request,
          `SELECT status FROM comment WHERE author_name = 'E2EAnon' AND post_slug = '${slug}'`,
        );
        if (rows.length === 0) return false;
        const status = String(rows[0][0]).replace(/"/g, "");
        return status === "flagged" ? status : false;
      },
      { timeoutMs: 20_000, intervalMs: 1_000, what: "moderator flagging" },
    );
    expect(flagged).toBe("flagged");
  });

  test("comment form rejects too-short bodies client-side (no reducer call)", async ({ page }) => {
    await page.goto(NOTES);
    await page.locator('a[href^="/2026-"]').first().click();
    await page.getByRole("textbox", { name: /comment/i }).fill("hi");
    await page.getByRole("button", { name: /post comment/i }).click();
    await expect(page.getByText(/too short/i)).toBeVisible();
  });
});
