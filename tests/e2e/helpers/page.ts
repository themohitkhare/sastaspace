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
  // domcontentloaded (not networkidle) — Cloudflare auto-injects an
  // analytics beacon (static.cloudflareinsights.com/beacon.min.js) that
  // our CSP blocks, so networkidle never fires (the failed beacon keeps
  // retrying). DOMContentLoaded + a short hydration wait is enough for
  // React to finish wiring up event handlers.
  await page.goto(url, { waitUntil: "domcontentloaded" });
  await page.waitForFunction(() => document.readyState === "interactive" || document.readyState === "complete");
  await page.waitForTimeout(400);
}

/** After clicking a link that navigates within the same SPA. */
export async function waitForHydrate(page: Page): Promise<void> {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(400);
}
