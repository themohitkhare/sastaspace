// Phase 2 F4 — /lab/deck happy-path spec.
//
// Runs in two modes determined by E2E_DECK_FLOW:
//   - "legacy" (default): the page calls services/deck via HTTP, or falls
//     back to the local procedural draft if NEXT_PUBLIC_DECK_API_URL is
//     unset. Always succeeds (the draft path is offline-safe).
//   - "stdb": the page (built with NEXT_PUBLIC_USE_STDB_DECK=true) routes
//     /plan + /generate through SpacetimeDB reducers. Requires the W3
//     deck-agent worker to be running with WORKER_DECK_AGENT_ENABLED=true.
//
// Acceptance: both invocations must pass. See
// docs/superpowers/plans/2026-04-26-stdb-native-phase2-f4-deck.md task 6.

import { test, expect } from "@playwright/test";
import path from "node:path";
import { LANDING } from "../helpers/urls.js";

const FLOW = process.env.E2E_DECK_FLOW ?? "legacy";
const AUTH_BACKEND = (process.env.E2E_AUTH_BACKEND ?? "fastapi").toLowerCase();

test.describe(`/lab/deck (${FLOW})`, () => {
  test.skip(
    AUTH_BACKEND === "stdb" && FLOW === "legacy",
    "/lab/deck legacy flow depends on services/deck FastAPI which Phase 4 deletes; switch to E2E_DECK_FLOW=stdb once deck-agent worker is verified",
  );
  test("submit brief → plan appears → generate → zip downloads", async ({
    page,
  }) => {
    // MusicGen render is slow on first run when FLOW=stdb; legacy is fast.
    test.setTimeout(8 * 60_000);

    await page.goto(`${LANDING}/lab/deck`);

    // Composer textarea.
    const textarea = page.getByRole("textbox").first();
    await expect(textarea).toBeVisible();
    await textarea.fill(
      "A meditation app for stressed professionals. Calm, slow, soft pads, no percussion.",
    );

    // Step 1 → Step 2 (planning → plan).
    await page.getByRole("button", { name: /^plan tracks$/i }).click();

    // The animation forces a min ~1.7s; allow up to 60s for the STDB
    // worker to flip the row, or for the legacy /plan call to return.
    await expect(
      page.getByRole("heading", { name: /here.*s what the deck wants/i }),
    ).toBeVisible({ timeout: 60_000 });

    // At least one planned track row should be visible (planList is the
    // wrapper; the planItem children carry the track names).
    const trackName = page.locator("[class*='planName']").first();
    await expect(trackName).toBeVisible();

    // Step 2 → Step 3 (plan → generating → results).
    await page.getByRole("button", { name: /generate audio/i }).click();

    // GeneratingView is a transient ~1-2s animation; then "download .zip"
    // appears in the Results view.
    await expect(
      page.getByRole("button", { name: /^download \.zip$/i }),
    ).toBeVisible({ timeout: 30_000 });

    // Click download, intercept the resulting download.
    const downloadPromise = page.waitForEvent("download", {
      timeout: FLOW === "stdb" ? 5 * 60_000 : 60_000,
    });
    await page.getByRole("button", { name: /^download \.zip$/i }).click();
    const download = await downloadPromise;

    // Save and verify it's non-trivial (>100 bytes for legacy stub;
    // >1KB for real zip via STDB worker).
    const dest = path.join(
      test.info().outputDir,
      await download.suggestedFilename(),
    );
    await download.saveAs(dest);
    const fs = await import("node:fs/promises");
    const stat = await fs.stat(dest);
    if (FLOW === "stdb") {
      expect(stat.size).toBeGreaterThan(1024); // real zip with WAVs
    } else {
      expect(stat.size).toBeGreaterThan(100); // legacy stub or real zip
    }

    // Result label should reflect success.
    await expect(
      page.getByRole("button", { name: /downloaded ✓/i }),
    ).toBeVisible({ timeout: 10_000 });
  });

  test("very-short brief disables the plan button", async ({ page }) => {
    await page.goto(`${LANDING}/lab/deck`);
    const textarea = page.getByRole("textbox").first();
    await textarea.fill("hi"); // < 4 chars
    const btn = page.getByRole("button", { name: /^plan tracks$/i });
    await expect(btn).toBeDisabled();
  });
});
