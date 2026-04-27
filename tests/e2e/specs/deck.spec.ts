// /lab/deck happy-path spec.
//
// Runs in one supported mode:
//   - "stdb" (recommended): the page (built with
//     NEXT_PUBLIC_USE_STDB_DECK=true) routes /plan + /generate through
//     SpacetimeDB reducers. Requires the W3 deck-agent worker to be
//     running with WORKER_DECK_AGENT_ENABLED=true and a real audio
//     backend behind LocalAI.
//
// Legacy FastAPI mode (E2E_DECK_FLOW=legacy) is skipped: the placeholder
// renderer was removed on 2026-04-27 because it produced fake "default
// sounds" that masked broken pipelines. /generate now returns 503 unless
// musicgen is wired into services/deck — services/deck itself is on the
// Phase 4 deletion list.

import { test, expect } from "@playwright/test";
import path from "node:path";
import { LANDING } from "../helpers/urls.js";

const FLOW = process.env.E2E_DECK_FLOW ?? "legacy";

test.describe(`/lab/deck (${FLOW})`, () => {
  test.skip(
    FLOW === "legacy",
    "/lab/deck legacy FastAPI flow returns 503 since the placeholder renderer was removed (2026-04-27); use E2E_DECK_FLOW=stdb against a deck-agent worker",
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

    // The generating phase now actually waits for the worker to render +
    // zip + unpack client-side before showing the download button. Allow
    // the same 5min budget the worker needs to render real WAVs.
    await expect(
      page.getByRole("button", { name: /^download \.zip$/i }),
    ).toBeVisible({ timeout: 5 * 60_000 });

    // Click download, intercept the resulting download. The blob is
    // already in memory at this point so the download triggers
    // immediately.
    const downloadPromise = page.waitForEvent("download", { timeout: 30_000 });
    await page.getByRole("button", { name: /^download \.zip$/i }).click();
    const download = await downloadPromise;

    // Save and verify it's a real zip (>1KB).
    const dest = path.join(
      test.info().outputDir,
      await download.suggestedFilename(),
    );
    await download.saveAs(dest);
    const fs = await import("node:fs/promises");
    const stat = await fs.stat(dest);
    expect(stat.size).toBeGreaterThan(1024); // real zip with WAVs

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
