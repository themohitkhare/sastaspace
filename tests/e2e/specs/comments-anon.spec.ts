import { expect, test } from "@playwright/test";
import { gotoAndHydrate, waitForHydrate } from "../helpers/page.js";
import { NOTES } from "../helpers/urls.js";

/**
 * Anonymous visitors no longer post directly — the form is gated behind
 * sign-in to keep spam off the moderator queue. These tests verify the
 * gate is shown and clicking it opens the sign-in modal.
 */

test.describe("comments — anonymous visitor sees sign-in gate", () => {
  async function openFirstPost(page: import("@playwright/test").Page): Promise<string> {
    await gotoAndHydrate(page, NOTES);
    const firstPostLink = page.locator('a[href^="/2026-"]').first();
    const slug = (await firstPostLink.getAttribute("href"))!.replace(/^\//, "");
    await firstPostLink.click();
    await page.waitForURL(new RegExp(`${slug}/?$`));
    await waitForHydrate(page);
    return slug;
  }

  test("anon user sees the sign-in gate, not a comment textarea", async ({ page }) => {
    await openFirstPost(page);
    // Comment textarea must not be present for anon users
    await expect(page.getByRole("textbox", { name: /^comment$/i })).toHaveCount(0);
    // Gate copy + sign-in CTA visible
    await expect(page.getByText(/sign in to leave a comment/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /sign in to comment/i })).toBeVisible();
  });

  test("clicking the gate's sign-in button opens the auth modal", async ({ page }) => {
    await openFirstPost(page);
    await page.getByRole("button", { name: /sign in to comment/i }).click();
    // Auth modal becomes visible
    await expect(page.getByRole("dialog", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/^email$/i)).toBeVisible();
  });
});
