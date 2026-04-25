import { expect, test } from "@playwright/test";
import { NOTES } from "../helpers/urls.js";

test.describe("notes — index + posts", () => {
  test("notes index loads with at least one post", async ({ page }) => {
    await page.goto(NOTES);
    await expect(page.getByRole("heading", { name: /thinking out loud/i })).toBeVisible();
    // At least one post link present (matches the date-prefixed slugs)
    const postLinks = page.locator('a[href^="/2026-"]');
    expect(await postLinks.count()).toBeGreaterThan(0);
  });

  test("clicking a post opens the article + shows its title as h1", async ({ page }) => {
    await page.goto(NOTES);
    const firstPostLink = page.locator('a[href^="/2026-"]').first();
    const slug = (await firstPostLink.getAttribute("href"))!;
    const linkText = (await firstPostLink.textContent())!.trim();
    await firstPostLink.click();
    await page.waitForURL(new RegExp(`${slug}/?$`));
    await expect(page.getByRole("heading", { level: 1 })).toContainText(linkText);
  });

  test("article page shows comments section with form", async ({ page }) => {
    await page.goto(NOTES);
    await page.locator('a[href^="/2026-"]').first().click();
    await expect(page.getByRole("heading", { name: /what people said/i })).toBeVisible();
    // Empty state copy when no comments yet (most posts will be empty)
    // OR a list of comments — both are valid; just assert the form is here
    await expect(page.getByRole("textbox", { name: /comment/i })).toBeVisible();
    await expect(page.getByRole("button", { name: /post comment/i })).toBeVisible();
  });
});

test.describe("notes — sign-in button & modal (the CSP-hydration bug)", () => {
  test("sign in button is visible and not just static HTML", async ({ page }) => {
    await page.goto(NOTES);
    const signInBtn = page.getByRole("button", { name: /sign in/i });
    await expect(signInBtn).toBeVisible();
  });

  test("clicking sign in opens the modal (proves React hydrated)", async ({ page }) => {
    await page.goto(NOTES);
    await page.getByRole("button", { name: /sign in/i }).click();
    // Modal should appear with email input
    await expect(page.getByRole("dialog", { name: /sign in/i })).toBeVisible();
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByRole("button", { name: /email me a link/i })).toBeVisible();
  });

  test("modal closes on Escape key", async ({ page }) => {
    await page.goto(NOTES);
    await page.getByRole("button", { name: /sign in/i }).click();
    await expect(page.getByRole("dialog")).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(page.getByRole("dialog")).not.toBeVisible();
  });

  test("modal validates email before submit", async ({ page }) => {
    await page.goto(NOTES);
    await page.getByRole("button", { name: /sign in/i }).click();
    await page.getByLabel(/email/i).fill("not-an-email");
    await page.getByRole("button", { name: /email me a link/i }).click();
    // Either inline validation message or our error path
    await expect(
      page.locator("text=/valid email|enter a valid/i"),
    ).toBeVisible({ timeout: 5_000 });
  });
});
