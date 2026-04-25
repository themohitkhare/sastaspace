/**
 * Page-level helpers — most importantly, the hydration wait.
 *
 * Without it, tests on the self-hosted runner race React hydration:
 * the test fills + clicks before the onSubmit handler is bound, the
 * form submits natively to the same URL, page reloads, React state
 * resets, and the assertion fires against a fresh form instead of
 * the post-click state. Locally everything's fast enough that the
 * race doesn't show.
 */

import type { Page } from "@playwright/test";

export async function gotoAndHydrate(page: Page, url: string): Promise<void> {
  await page.goto(url, { waitUntil: "networkidle" });
  // Hydration completes in microtasks AFTER networkidle. Give it a bit.
  await page.waitForFunction(() => document.readyState === "complete");
  await page.waitForTimeout(150);
}

/** After clicking a link that navigates within the same SPA. */
export async function waitForHydrate(page: Page): Promise<void> {
  await page.waitForLoadState("networkidle");
  await page.waitForTimeout(150);
}
