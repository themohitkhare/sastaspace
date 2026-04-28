import { expect, test } from "@playwright/test";
import {
  enterFirstRegion,
  exitBattle,
  freshContext,
  gotoTypewars,
  randomCallsign,
  registerPlayer,
  waitForFirstWord,
} from "../helpers/typewars.js";

test.describe("typewars · Battle (WPM, accuracy, words, exit)", () => {
  test.beforeEach(async ({ page }) => {
    await freshContext(page);
    await gotoTypewars(page);
    await registerPlayer(page, "Wardens", randomCallsign());
    await enterFirstRegion(page);
  });

  test("HUD shows initial WPM=0, ACC=100%, DMG=0 before any input", async ({ page }) => {
    const wpm = page.locator(".hud-stat", { hasText: "WPM" }).locator(".hud-val");
    const acc = page.locator(".hud-stat", { hasText: "ACC" }).locator(".hud-val");
    const dmg = page.locator(".hud-stat", { hasText: "DMG" }).locator(".hud-val");
    await expect(wpm).toHaveText("0");
    await expect(acc).toHaveText("100%");
    await expect(dmg).toHaveText("0");
  });

  test("region HP bar + 5-legion contribution legend render from live region row", async ({
    page,
  }) => {
    await expect(page.locator(".region-hp-wrap")).toBeVisible();
    await expect(page.locator(".hp-bar-outer")).toBeVisible();
    await expect(page.locator(".contrib-bar")).toBeVisible();
  });

  test("server spawns word cards via subscription", async ({ page }) => {
    const text = await waitForFirstWord(page);
    expect(text.length).toBeGreaterThan(0);
    // At least one card; battle starts with a small initial pool.
    expect(await page.locator(".word-card").count()).toBeGreaterThanOrEqual(1);
  });

  test("typing a word + space submits, streak increments, DMG > 0", async ({ page }) => {
    const word = await waitForFirstWord(page);
    const input = page.locator(".battle-input");
    await input.focus();
    await input.fill(word);
    await input.press("Space");

    // Streak transitions 0 → 1 once submit_word reducer commits server-side.
    const streakNum = page.locator(".streak-card .streak-num");
    await expect(streakNum).not.toHaveText("0", { timeout: 5_000 });

    // Damage accumulates after a successful submit.
    const dmg = page.locator(".hud-stat", { hasText: "DMG" }).locator(".hud-val");
    await expect(dmg).not.toHaveText("0", { timeout: 5_000 });
  });

  test("WPM rises above 0 after a successful word submit", async ({ page }) => {
    const word = await waitForFirstWord(page);
    const input = page.locator(".battle-input");
    await input.fill(word);
    await input.press("Space");

    const wpm = page.locator(".hud-stat", { hasText: "WPM" }).locator(".hud-val");
    // WPM = hits / elapsedMin. After 1 hit and ~1s, WPM ≈ 60.
    await expect(wpm).not.toHaveText("0", { timeout: 5_000 });
  });

  test("typing wrong word increments accuracy misses (ACC drops)", async ({ page }) => {
    await waitForFirstWord(page);
    const input = page.locator(".battle-input");
    await input.fill("zzzzzzzzz-not-a-real-word");
    await input.press("Space");

    const acc = page.locator(".hud-stat", { hasText: "ACC" }).locator(".hud-val");
    await expect(acc).not.toHaveText("100%", { timeout: 5_000 });
  });

  test("exit button returns to warmap and ends server session", async ({ page }) => {
    await waitForFirstWord(page);
    await exitBattle(page);
  });
});
