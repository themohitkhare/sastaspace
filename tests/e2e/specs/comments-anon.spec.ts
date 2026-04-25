import { expect, test } from "@playwright/test";
import { gotoAndHydrate, waitForHydrate } from "../helpers/page.js";
import { sql, pollUntil } from "../helpers/stdb.js";
import { NOTES } from "../helpers/urls.js";

/**
 * Anonymous comment flow:
 *   1. Open a post page (waiting for React to hydrate)
 *   2. Submit a benign comment via the form
 *   3. Confirm the form transitions to the "queued, moderator reviewing" state
 *   4. Poll stdb directly until the moderator approves it (~3-5s)
 *
 * Cleans up smoke comments in afterEach so the live admin queue stays tidy.
 */

test.describe("comments — anonymous post + moderator", () => {
  test.beforeAll(async ({ request }) => {
    await sql(request, `DELETE FROM comment WHERE author_name = 'E2EAnon'`).catch(() => {});
  });

  test.afterEach(async ({ request }) => {
    await sql(request, `DELETE FROM comment WHERE author_name = 'E2EAnon'`).catch(() => {});
  });

  /** Common setup: open the first post page with hydration complete. */
  async function openFirstPost(page: import("@playwright/test").Page): Promise<string> {
    await gotoAndHydrate(page, NOTES);
    const firstPostLink = page.locator('a[href^="/2026-"]').first();
    const slug = (await firstPostLink.getAttribute("href"))!.replace(/^\//, "");
    await firstPostLink.click();
    await page.waitForURL(new RegExp(`${slug}/?$`));
    await waitForHydrate(page);
    return slug;
  }

  test("anon comment goes to pending → moderator approves within 20s", async ({ page, request }) => {
    const slug = await openFirstPost(page);
    const body = `e2e smoke at ${new Date().toISOString()} — totally benign content`;

    await page.getByLabel(/^name/i).fill("E2EAnon");
    await page.getByRole("textbox", { name: /^comment$/i }).fill(body);
    await page.getByRole("button", { name: /post comment/i }).click();

    await expect(page.getByText(/moderator's looking it over/i)).toBeVisible({
      timeout: 15_000,
    });

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
      { timeoutMs: 25_000, intervalMs: 1_000, what: "moderator approval" },
    );
    expect(approved).toBe("approved");
  });

  test("spam comment goes to pending → moderator flags within 20s", async ({ page, request }) => {
    const slug = await openFirstPost(page);
    const spam = `BUY CHEAP MEDS at http://spam.example NOW NOW NOW click click click`;

    await page.getByLabel(/^name/i).fill("E2EAnon");
    await page.getByRole("textbox", { name: /^comment$/i }).fill(spam);
    await page.getByRole("button", { name: /post comment/i }).click();

    await expect(page.getByText(/moderator's looking it over/i)).toBeVisible({
      timeout: 15_000,
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
      { timeoutMs: 25_000, intervalMs: 1_000, what: "moderator flagging" },
    );
    expect(flagged).toBe("flagged");
  });

  test("comment form rejects too-short bodies client-side (no reducer call)", async ({ page }) => {
    await openFirstPost(page);
    await page.getByRole("textbox", { name: /^comment$/i }).fill("hi");
    await page.getByRole("button", { name: /post comment/i }).click();
    // Our React validation sets state.kind = "error" → renders error span
    await expect(page.locator(".comments-module__hmuBla__error, [class*='_error']").first()).toBeVisible(
      { timeout: 5_000 },
    );
    await expect(page.getByText(/too short/i)).toBeVisible();
  });
});
