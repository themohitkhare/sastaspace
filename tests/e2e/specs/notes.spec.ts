import { expect, test } from "@playwright/test";
import { gotoAndHydrate, waitForHydrate } from "../helpers/page.js";
import { NOTES } from "../helpers/urls.js";

test.describe("notes — index + posts", () => {
  test("notes index loads with at least one post", async ({ page }) => {
    await gotoAndHydrate(page, NOTES);
    await expect(page.getByRole("heading", { name: /thinking out loud/i })).toBeVisible();
    const postLinks = page.locator('a[href^="/2026-"]');
    expect(await postLinks.count()).toBeGreaterThan(0);
  });

  test("clicking a post opens the article + shows its title as h1", async ({ page }) => {
    await gotoAndHydrate(page, NOTES);
    const firstPostLink = page.locator('a[href^="/2026-"]').first();
    const slug = (await firstPostLink.getAttribute("href"))!;
    const linkText = (await firstPostLink.textContent())!.trim();
    await firstPostLink.click();
    await page.waitForURL(new RegExp(`${slug}/?$`));
    await expect(page.getByRole("heading", { level: 1 })).toContainText(linkText);
  });

  test("article page shows comments section with sign-in gate for anon users", async ({ page }) => {
    await gotoAndHydrate(page, NOTES);
    await page.locator('a[href^="/2026-"]').first().click();
    await waitForHydrate(page);
    await expect(page.getByRole("heading", { name: /what people said/i })).toBeVisible();
    // Unauthenticated: form shows sign-in gate, not the textarea.
    // Signed-in comment form is covered in comments-signed-in.spec.ts.
    await expect(page.getByRole("button", { name: /sign in to comment/i })).toBeVisible();
  });
});

test.describe("notes — sign-in button & modal (the CSP-hydration bug)", () => {
  test("sign in button is visible and not just static HTML", async ({ page }) => {
    await gotoAndHydrate(page, NOTES);
    const signInBtn = page.getByRole("button", { name: /sign in/i });
    await expect(signInBtn).toBeVisible();
  });

  test("clicking sign in opens the modal (proves React hydrated)", async ({ page }) => {
    await gotoAndHydrate(page, NOTES);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByRole("dialog", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /email me a link/i })).toBeVisible();
  });

  test("modal closes on Escape key", async ({ page }) => {
    await gotoAndHydrate(page, NOTES);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("modal blocks submit when email is invalid (browser validation OR react guard)", async ({ page }) => {
    // The email input is type="email" so the BROWSER blocks a malformed
    // value with a native validation popup before our React handler runs.
    // We can't see the native popup as a DOM element, so we assert the
    // modal stays put + the success state ("check inbox") never appears.
    await gotoAndHydrate(page, NOTES);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.getByLabel(/email/i).fill("not-an-email");
    await page.getByRole("button", { name: /email me a link/i }).click();
    // After click, we should NOT see the success state (because the form
    // didn't actually submit). The modal is still open and the "send a
    // link" button is still here.
    await page.waitForTimeout(500); // brief settle
    await expect(page.getByText(/check your inbox/i)).not.toBeVisible();
    await expect(page.getByRole("button", { name: /email me a link/i })).toBeVisible();
  });
});
